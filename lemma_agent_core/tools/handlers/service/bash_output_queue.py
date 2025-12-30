from dataclasses import dataclass, field
from typing import Optional
import time
import asyncio


@dataclass
class PendingBashOutput:
    """待上报的 bash output（快照）"""
    task_id: str
    tool_id: str
    session_id: str
    command: str
    output: str  # 输出快照
    exit_code: Optional[int] = None  # None=运行中, 非None=已完成
    is_final: bool = False  # 是否是最终结果
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0  # 重试次数

bash_output_queue: asyncio.Queue[PendingBashOutput] = asyncio.Queue()
