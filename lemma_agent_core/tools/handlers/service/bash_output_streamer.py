"""
Bash Output Streamer - 独立的 bash output 流式上报管理器

负责定期向后端上报 bash 命令的输出结果。
使用队列+生产者/消费者模式，确保 output 不会丢失。
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, TYPE_CHECKING
from support.py.bash_output import update_bash_session_output
from service.bash_output_queue import bash_output_queue, PendingBashOutput
import hashlib
from utils.config import LEMMA_CONFIG

if TYPE_CHECKING:
    from remote_tool_handler.bash_session_pyte import BashSessionManager
    from support.py.connection import AuthorizedHTTPConnection


from utils.logging_config import LoggerConfig
logger = logging.getLogger(__name__)


@dataclass
class CollectorSession:
    """活跃的采集 session"""
    task_id: str
    tool_id: str
    session_id: str
    bash_manager: 'BashSessionManager'
    command: str
    collector_task: Optional[asyncio.Task] = field(default=None)
    final_output_task: Optional[asyncio.Task] = field(default=None)
    finish_event: asyncio.Event = field(default=None)
    stop_requested: bool = field(default=False)


class BashOutputStreamer:
    """独立的 bash output 流式上报管理器
    
    使用队列+生产者/消费者模式：
    - 生产者（collector）：定时采集 output 并入队
    - 消费者（sender）：从队列取出并发送到后端
    
    这样设计确保：
    1. output 快照入队后不会丢失
    2. 即使新命令开始执行，已入队的 output 仍能正确发送
    3. final output 保证发送成功
    """
    
    def __init__(self, http_conn, toolkit_instance_id: str, interval: float = 3.0):
        """
        初始化 BashOutputStreamer
        
        Args:
            http_conn: AuthorizedHTTPConnection 实例
            toolkit_instance_id: toolkit 实例 ID
            interval: 上报间隔（秒），默认 3 秒
        """
        self.http_conn = http_conn
        self.toolkit_instance_id = toolkit_instance_id
        self.interval = interval
        
        # 发送协程
        self.sender_task: Optional[asyncio.Task] = None
        
        # 活跃的采集 sessions
        self.active_sessions: Dict[str, CollectorSession] = {}  # key: f"{task_id}:{session_id}"
        
        self._lock = asyncio.Lock()
        self.shutdown_event = asyncio.Event()
        self._started = False
        
    def _session_key(self, task_id: str, session_id: str) -> str:
        """生成 session 的唯一 key"""
        return f"{task_id}:{session_id}"
    
    def start(self) -> None:
        """启动发送协程（消费者）"""
        if self._started:
            return
        
        self._started = True
        self.sender_task = asyncio.create_task(self._sender_loop())
        logger.info("BashOutputStreamer started")
    
    async def _sender_loop(self) -> None:
        """消费者：从队列取出并发送到后端
        
        - 普通 output：发送失败则丢弃（下次会有新的）
        - final output：发送失败则重新入队，无限重试直到成功
        """
        logger.debug("Sender loop started")
        
        while not self.shutdown_event.is_set():
            try:
                # 从队列取出，超时 1 秒
                try:
                    pending = await asyncio.wait_for(
                        bash_output_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # 发送
                success = await self._send_output(pending)
                
                # final output 必须发送成功
                if pending.is_final and not success:
                    pending.retry_count += 1
                    logger.warning(f"Failed to send final output (retry #{pending.retry_count}), re-queuing...")
                    # 重新入队
                    await bash_output_queue.put(pending)
                elif success:
                    logger.debug(f"Output sent successfully for {pending.task_id}:{pending.session_id} (final={pending.is_final})")
                    
            except asyncio.CancelledError:
                logger.debug("Sender loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in sender loop: {e}", exc_info=True)
        
        logger.debug("Sender loop stopped")
    
    async def start_streaming(
        self,
        task_id: str,
        tool_id: str,
        session_id: str,
        command: str,
        bash_manager: 'BashSessionManager',
        finish_event: asyncio.Event
    ) -> None:
        """
        开始对某个 bash session 的流式上报
        
        启动一个 collector 协程，定时采集 output 并入队。
        当命令完成时，collector 会自动采集 final output 并入队。
        
        Args:
            task_id: 任务 ID
            tool_id: 工具 ID
            session_id: bash session 名称
            command: 执行的命令
            bash_manager: BashSessionManager 实例
            finish_event: 命令完成事件
        """
        key = self._session_key(task_id, session_id)
        
        async with self._lock:
            # 如果已有该 session 的采集任务，报错退出
            if key in self.active_sessions:
                raise ValueError(f"Session {key} already exists")
            
            # 创建新的采集 session
            session = CollectorSession(
                task_id=task_id,
                tool_id=tool_id,
                session_id=session_id,
                bash_manager=bash_manager,
                command=command,
                finish_event=finish_event
            )
            
            # 启动采集任务（生产者）
            session.collector_task = asyncio.create_task(self._collector_loop(session))
            self.active_sessions[key] = session
            session.final_output_task = asyncio.create_task(self.send_final_output(session))
            
            logger.info(f"Started streaming for session {key}")

    async def send_final_output(self, session: CollectorSession) -> None:
        """发送最终结果"""
        await session.finish_event.wait()
        logger.debug(f"Command completed for session {session.session_id}, sending final output")
        try:
            final_output = await session.bash_manager.get_last_cmd_output(session.session_id)
            exit_code = await session.bash_manager.get_last_cmd_exit_code(session.session_id)
        except Exception as e:
            logger.error(f"Error getting final output for session {session.session_id}: {e}")
            final_output = ""
            exit_code = 255

        try:
            await bash_output_queue.put(PendingBashOutput(
                task_id=session.task_id,
                tool_id=session.tool_id,
                session_id=session.session_id,
                command=session.command,
                output=final_output or "",
                exit_code=exit_code if exit_code is not None else 255,
                is_final=True
            ))
            logger.info(f"Final output queued for {session.task_id}:{session.session_id} with exit_code={exit_code}")
        except Exception as e:
            logger.error(f"Error queuing final output for {session.task_id}:{session.session_id}: {e}")
            raise
        finally:
            session.collector_task.cancel()
            session.stop_requested = True

    def get_md5(self, output: str) -> str:
        return hashlib.md5(output.encode('utf-8')).hexdigest()

    async def _wait_for_interval(self) -> None:
        """等待 interval"""
        try:
            await asyncio.wait_for(
                self.shutdown_event.wait(),
                timeout=self.interval
            )
        except asyncio.TimeoutError:
            pass
    
    async def _collector_loop(self, session: CollectorSession) -> None:
        """生产者：定时采集 output 并入队
        
        当命令完成时，自动采集 final output（带 exit code）并入队。
        """
        key = self._session_key(session.task_id, session.session_id)
        logger.debug(f"Collector loop started for {key}. stop_requested: {session.stop_requested}, shutdown_event: {self.shutdown_event.is_set()}")

        last_output_md5 = None
        
        try:
            while not session.stop_requested and not self.shutdown_event.is_set():
                # 获取当前输出
                try:
                    output = await session.bash_manager.get_current_cmd_output(session.session_id)
                    output_md5 = self.get_md5(output)
                    if last_output_md5 == output_md5:
                        await self._wait_for_interval()
                        continue
                    last_output_md5 = output_md5
                    
                except Exception as e:
                    logger.error(f"Error getting output for session {session.session_id}: {e}")
                    output = ""
                
                # 检查命令是否已完成
                # status = await session.bash_manager.status(session.session_id)
                # logger.debug(f"Status for session {session.session_id}: {status}")
                
                # if status != "running":
                if session.finish_event.is_set():
                    # 命令已完成，采集最终结果并入队
                    logger.debug(f"Command completed for session {session.session_id}, break")
                    break
                else:
                    # 命令还在运行，入队中间结果
                    logger.info(f"Putting output for {session.task_id}:{session.session_id}: (len: {len(output)})")
                    if LEMMA_CONFIG["debug"]:
                        import uuid, os
                        os.makedirs('tmp', exist_ok=True)
                        with open(f'tmp/bash_output_{uuid.uuid4().hex}.txt', 'w', encoding='utf-8') as bash_output_file:
                            bash_output_file.write(output)
                    await bash_output_queue.put(PendingBashOutput(
                        task_id=session.task_id,
                        tool_id=session.tool_id,
                        session_id=session.session_id,
                        command=session.command,
                        output=output,
                        exit_code=None,
                        is_final=False
                    ))
                
                await self._wait_for_interval()
                    
        except asyncio.CancelledError:
            logger.debug(f"Collector loop cancelled for {key}")
            raise
        except Exception as e:
            logger.error(f"Error in collector loop for {key}: {e}", exc_info=True)
        finally:
            # 清理
            async with self._lock:
                self.active_sessions.pop(key, None)
            logger.debug(f"Collector loop stopped for {key}")
    
    async def _send_output(self, pending: PendingBashOutput) -> bool:
        """
        发送 bash output 到后端
        
        Args:
            pending: PendingBashOutput 实例
            
        Returns:
            是否发送成功
        """
        try:
            logger.debug(f"Sending output for {pending.task_id}:{pending.session_id}: {pending.output[:100]}... (len: {len(pending.output)}), exit_code: {pending.exit_code}")
            await asyncio.to_thread(
                update_bash_session_output,
                authed_connection=self.http_conn,
                task_id=pending.task_id,
                tool_id=pending.tool_id,
                bash_session=pending.session_id,
                bash_session_command=pending.command,
                bash_session_command_output=pending.output,
                bash_session_command_ret_code=pending.exit_code
            )
            return True
        except Exception as e:
            logger.error(f"Error sending output for {pending.task_id}:{pending.session_id}: {e}")
            return False
    
    async def shutdown(self, timeout: float = 8.0) -> None:
        """
        优雅关闭：等待所有 final output 发送完成
        
        Args:
            timeout: 超时时间（秒），默认 8 秒
        """
        logger.info(f"Shutting down BashOutputStreamer with timeout {timeout}s")
        
        # 设置 shutdown 事件，通知所有循环停止
        self.shutdown_event.set()
        
        # 等待所有 collector 任务完成（它们会在退出前入队 final output）
        async with self._lock:
            collector_tasks = [
                s.collector_task for s in self.active_sessions.values()
                if s.collector_task and not s.collector_task.done()
            ]
            collector_tasks += [
                s.final_output_task for s in self.active_sessions.values()
                if s.final_output_task and not s.final_output_task.done()
            ]

        if collector_tasks:
            logger.info(f"Waiting for {len(collector_tasks)} collector tasks to finish...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*collector_tasks, return_exceptions=True),
                    timeout=2.0  # 给 collector 2 秒时间完成
                )
            except asyncio.TimeoutError:
                logger.warning("Collector tasks timed out, cancelling...")
                for task in collector_tasks:
                    task.cancel()
        
        # 等待队列中的 final output 发送完成
        start_time = time.time()
        remaining_timeout = timeout - (time.time() - start_time)
        
        while remaining_timeout > 0:
            # 检查队列中是否还有 final output
            has_final = False
            temp_items = []
            
            while not bash_output_queue.empty():
                try:
                    item = bash_output_queue.get_nowait()
                    if item.is_final:
                        has_final = True
                        temp_items.append(item)
                except asyncio.QueueEmpty:
                    break
            
            # 把 items 放回队列
            for item in temp_items:
                await bash_output_queue.put(item)
            
            if not has_final:
                logger.info("All final outputs have been sent")
                break
            
            # 等待一小段时间让 sender 处理
            await asyncio.sleep(0.5)
            remaining_timeout = timeout - (time.time() - start_time)
        
        if remaining_timeout <= 0:
            logger.warning(f"Shutdown timeout ({timeout}s) reached, some final outputs may not have been sent")
        
        # 停止 sender
        if self.sender_task and not self.sender_task.done():
            self.sender_task.cancel()
            try:
                await self.sender_task
            except asyncio.CancelledError:
                pass
        
        # 清理
        async with self._lock:
            self.active_sessions.clear()
        
        self._started = False
        logger.info("BashOutputStreamer shutdown complete")


_BASH_OUTPUT_STREAMER: Optional[BashOutputStreamer] = None

def get_bash_output_streamer() -> BashOutputStreamer:
    """Get the bash output streamer"""
    global _BASH_OUTPUT_STREAMER
    if _BASH_OUTPUT_STREAMER is None:
        raise RuntimeError("BashOutputStreamer not initialized")
    return _BASH_OUTPUT_STREAMER


def initialize_bash_output_streamer(http_conn: 'AuthorizedHTTPConnection', toolkit_instance_id: str) -> None:
    """Initialize the bash output streamer"""
    global _BASH_OUTPUT_STREAMER
    if _BASH_OUTPUT_STREAMER is not None:
        raise RuntimeError("BashOutputStreamer already initialized")
    _BASH_OUTPUT_STREAMER = BashOutputStreamer(
        http_conn=http_conn,
        toolkit_instance_id=toolkit_instance_id
    )
    _BASH_OUTPUT_STREAMER.start()
    logger.info("BashOutputStreamer initialized")
