import os
import time
import logging
from typing import Optional, List, Dict, Any
# from remote_tool_handler.bash_session import get_bash_manager, cleanup_bash_manager
from bash_session_pyte import get_bash_manager
# Simplified: disable file watcher for research version
# from service.file_watcher import FileWatcher, FileChange
# from service.bash_output_streamer import get_bash_output_streamer
import asyncio

# Stub class for FileChange since we're not using file watcher
class FileChange:
    def __init__(self, path: str, change_type: str):
        self.path = path
        self.change_type = change_type

class ToolState():
    def __init__(self, task_id: str, working_dir: str):
        self.type = 'remote_tool_state'
        self.logger = logging.getLogger(__name__)
        self._files_read = set()
        self._file_read_timestamps = {}
        self.original_working_dir = working_dir
        self.task_id = task_id
        # Bash manager for this task's Bash Sessions (windows)
        self._bash_manager = None  # Will be initialized on first use
        # File watcher for tracking user changes to files
        self._file_watcher: Optional[FileWatcher] = None

    def get_working_dir(self) -> str:
        """Get the working directory"""
        return self.original_working_dir

    async def start_task(self):
        await asyncio.sleep(0.0)
        # TODO: add file_watcher support 
        # await self.start_file_watcher()

    # -------------------- bash session management APIs --------------------
    def get_bash_manager(self):
        """Return the bash manager for this task, ensuring working_dir is current."""
        if self._bash_manager is None:
            # Use the global registry to ensure cleanup works properly
            self._bash_manager = get_bash_manager(task_id=self.task_id, working_dir=self.get_working_dir())
        return self._bash_manager

    async def get_current_cmd_output(self, session_id: str) -> str:
        mgr = self.get_bash_manager()
        return await mgr.get_current_cmd_output(session_id)

    async def get_last_cmd_output(self, session_id: str) -> str | None:
        mgr = self.get_bash_manager()
        return await mgr.get_last_cmd_output(session_id)

    async def get_last_cmd_exit_code(self, session_id: str) -> int | None:
        mgr = self.get_bash_manager()
        return await mgr.get_last_cmd_exit_code(session_id)

    async def bash_status(self, session_id: str) -> Dict[str, Any]:
        mgr = self.get_bash_manager()
        return await mgr.status(session_id)

    async def bash_run_command(self, command: str, session_id: Optional[str], timeout: float, tool_id: str) -> Dict[str, Any]:
        mgr = self.get_bash_manager()
        finish_event = asyncio.Event()
        # Simplified: no streaming for research version
        # streamer = get_bash_output_streamer()
        # await streamer.start_streaming(...)
        return await mgr.run_command(command=command, window_name=session_id, timeout=timeout, finish_event=finish_event)

    async def bash_read_output(self, session_id: str, incremental: bool = True) -> tuple:
        mgr = self.get_bash_manager()
        return await mgr.read_output(session_id, incremental=incremental)

    async def bash_list_windows(self) -> List[Any]:
        mgr = self.get_bash_manager()
        return await mgr.list_windows()

    async def bash_kill(self, session_id: str, end_session: bool) -> Dict[str, Any]:
        mgr = self.get_bash_manager()
        ok, msg = await mgr.kill(session_id, end_session)
        return {"ok": ok, "message": msg}
    
    # -------------------- File management APIs --------------------

    def mark_file_as_read(self, file_path: str) -> None:
        """Mark a file as having been read"""
        abs_path = os.path.abspath(file_path)
        self._files_read.add(abs_path)
        self._file_read_timestamps[abs_path] = time.time()
    
    def is_file_read(self, file_path: str) -> bool:
        """Check if a file has been read"""
        return os.path.abspath(file_path) in self._files_read
    
    def is_file_read_fresh(self, file_path: str) -> bool:
        """Check if a file has been read and the read is still fresh (file hasn't been modified since read)"""
        abs_path = os.path.abspath(file_path)
        
        # Check if file was read at all
        if abs_path not in self._files_read:
            return False
        
        # Check if file still exists
        if not os.path.exists(abs_path):
            return False
        
        try:
            # Get file modification time
            file_mtime = os.path.getmtime(abs_path)
            # Get read timestamp
            read_time = self._file_read_timestamps.get(abs_path, 0)
            
            # File is fresh if it was read after the last modification
            # Allow small tolerance (1 second) for potential timing issues
            return read_time >= (file_mtime - 1.0)
        except OSError:
            # If we can't get file stats, consider it not fresh
            return False

    async def write_file(self, file_path: str, content: str) -> None:
        """Write a file"""
        abs_path = os.path.abspath(file_path)
        if self._file_watcher is not None:
            await self._file_watcher.add_ignore_edit(abs_path, content)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.mark_file_as_read(file_path)

    # -------------------- File watcher management APIs --------------------
    
    async def start_file_watcher(self) -> None:
        """
        Start watching for file changes in the working directory.
        
        Changes are accumulated and can be retrieved later with get_pending_file_changes().
        Files that are modified and then reverted to their original state will be
        automatically filtered out.
        """
        if self._file_watcher is not None and self._file_watcher.is_running():
            self.logger.warning(f"File watcher already running for task {self.task_id}")
            return
        
        working_dir = self.get_working_dir()
        if not working_dir or not os.path.isdir(working_dir):
            self.logger.warning(f"Cannot start file watcher: invalid working_dir '{working_dir}'")
            return
        
        self._file_watcher = FileWatcher(working_dir)
        
        await self._file_watcher.start()
        self.logger.info(f"File watcher started for task {self.task_id} at {working_dir}")
    
    async def stop_file_watcher(self) -> None:
        """
        Stop watching for file changes.
        
        Note: This does NOT flush pending changes. Call get_pending_file_changes()
        before stopping if you need to retrieve accumulated changes.
        """
        if self._file_watcher is not None:
            await self._file_watcher.stop()
            self.logger.info(f"File watcher stopped for task {self.task_id}")
        
        self._file_watcher = None
    
    def has_pending_file_changes(self) -> bool:
        """
        Check if there are any pending file changes.
        
        Returns:
            True if there are accumulated file changes waiting to be processed
        """
        if self._file_watcher is None:
            return False
        return self._file_watcher.has_pending_changes()
    
    async def get_pending_file_changes(self) -> List[FileChange]:
        """
        Get and flush all pending file changes.
        
        This merges accumulated changes and applies smart filtering:
        - Files that were modified and then reverted to original state are excluded
        - Multiple changes to the same file are merged into a single change
        - Diff summaries are generated for modified files
        
        Returns:
            List of FileChange objects representing the net changes since last flush
        """
        if self._file_watcher is None:
            return []
        return await self._file_watcher.merge_and_flush()
    
    def get_pending_file_changes_count(self) -> int:
        """
        Get the number of files with pending changes.
        
        Returns:
            Number of files with accumulated changes
        """
        if self._file_watcher is None:
            return 0
        return self._file_watcher.pending_count
    
    def is_file_watcher_running(self) -> bool:
        """
        Check if the file watcher is currently running.
        
        Returns:
            True if the file watcher is active
        """
        return self._file_watcher is not None and self._file_watcher.is_running()

    # -------------------- Other APIs --------------------
    
    async def terminate(self):
        """Terminate the tool state and cleanup resources"""
        # Stop file watcher
        if self._file_watcher is not None:
            try:
                await self.stop_file_watcher()
            except Exception as e:
                self.logger.error(f"Failed to stop file watcher: {e}")
        
        # # Clean up bash manager for this task
        # if self._bash_manager is not None:
        #     try:
        #         await cleanup_bash_manager(self.task_id)
        #         self._bash_manager = None
        #     except Exception as e:
        #         self.logger.error(f"Failed to cleanup bash manager: {e}")
    
    def task_state_to_dict(self) -> Dict[str, Any]:
        """Save task tool state to a JSON file"""
        if not self._files_read:
            return None
        
        # Convert sets to lists for JSON serialization
        return {
            "working_dir": "",
            "task_id": "",
            "tool_state": {
                "files_read": list(self._files_read),
                "file_read_timestamps": self._file_read_timestamps,
            }
        }

    def load_task_state(self, state_data: dict) -> None:
        """Load task tool state from a state dictionary"""
        try:
            # Validate the structure
            if "working_dir" not in state_data or "tool_state" not in state_data:
                raise ValueError(f"Invalid state file format: missing required fields for tool_state: {state_data}")
            
            tool_state = state_data["tool_state"]
            if "files_read" not in tool_state or "file_read_timestamps" not in tool_state:
                raise ValueError(f"Invalid state file format: missing tool_state fields: {tool_state}")
            
            # Load the data
            self._files_read = set(tool_state["files_read"])
            self._file_read_timestamps = tool_state["file_read_timestamps"]
            
            # Update working directory if different
            saved_working_dir = state_data["working_dir"]
            if saved_working_dir and saved_working_dir != self.get_working_dir():
                # Note: We don't change the bash session's working directory here
                # as it might be actively running commands. The caller should handle
                # directory changes if needed.
                self.logger.warning(f"Working directory is different from saved working directory: {self.get_working_dir()} -> {saved_working_dir}")
                
        except Exception as e:
            raise Exception(f"Failed to load task state from {state_data}: {e}")
