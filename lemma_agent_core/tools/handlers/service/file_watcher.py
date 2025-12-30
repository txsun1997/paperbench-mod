"""
File Watcher Module
====================
This module provides file watching functionality using watchfiles library.
It accumulates file changes and supports smart merging to detect files
that were modified and then reverted to their original state.
"""

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from watchfiles import DefaultFilter, awatch, Change
import time
import uuid


# from utils.logging_config import LoggerConfig
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 1024 * 1024 * 5  # 5MB

@dataclass
class FileChange:
    """Represents a single file change"""
    path: str                    # Relative path from working_dir
    path_absolute: str           # Absolute path
    change_type: Change          # Type of change
    timestamp: float             # When the change occurred


# Directories to ignore when watching
IGNORE_DIRS: Set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".env",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    "egg-info",
    ".eggs",
}


# File patterns to ignore (regex patterns for watchfiles)
# Note: These must be valid regex patterns, not glob patterns
IGNORE_PATTERNS: Set[str] = {
    r".*\.pyc$",
    r".*\.pyo$",
    r".*\.pyd$",
    r".*\.so$",
    r".*\.dll$",
    r".*\.dylib$",
    r".*\.log$",
    r".*\.tmp$",
    r".*\.temp$",
    r".*\.swp$",
    r".*\.swo$",
    r"\.DS_Store$",
    r"Thumbs\.db$",
    r".*\.lock$",
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"pnpm-lock\.yaml$",
    r".*\.egg-info$",

    # Image files
    r".*\.jpg$",
    r".*\.jpeg$",
    r".*\.png$",
    r".*\.gif$",
    r".*\.bmp$",
    r".*\.webp$",
    r".*\.ico$",
    r".*\.svg$",

    # Video files
    r".*\.mp4$",
    r".*\.mov$",
    r".*\.avi$",
    r".*\.mkv$",
    r".*\.webm$",
    r".*\.flv$",
    r".*\.wmv$",
    r".*\.m4v$",

    # Audio files
    r".*\.mp3$",
    r".*\.wav$",
    r".*\.ogg$",
    r".*\.aac$",
    r".*\.m4a$",
    r".*\.flac$",
    r".*\.alac$",
    r".*\.ape$",

    # Document files
    r".*\.pdf$",

    # executable files
    r".*\.exe$",
    r".*\.bin$",
    r".*\.jar$",
    r".*\.war$",
    r".*\.zip$",
    r".*\.tar$",
    r".*\.gz$",
    r".*\.bz2$",
    r".*\.rar$",
    r".*\.7z$",
    r".*\.iso$",
    r".*\.dmg$",
    r".*\.pkg$",
    r".*\.deb$",
    r".*\.rpm$",
    r".*\.msi$",
}

class WatcherFilter(DefaultFilter):
    def __init__(self):
        for d in self.ignore_dirs:
            IGNORE_DIRS.add(d)
        for p in self.ignore_entity_patterns:
            IGNORE_PATTERNS.add(p)
        super().__init__(
            ignore_dirs=IGNORE_DIRS,
            ignore_entity_patterns=IGNORE_PATTERNS,
        )

def _compute_file_hash(file_path: str) -> Optional[str]:
    """Compute MD5 hash of file content"""
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            return _compute_content_hash(f.read())
    return None

def _compute_content_hash(content: bytes | str) -> str:
    """Compute MD5 hash of content"""
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.md5(content).hexdigest()


def _is_text_file(file_path: str, sample_size: int = 8192) -> bool:
    """
    Check if a file is a text file by attempting to decode it as UTF-8.
    
    Args:
        file_path: Path to the file
        sample_size: Number of bytes to sample for detection
    
    Returns:
        True if file appears to be a text file, False otherwise
    """
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)
        
        if not sample:
            # Empty file is considered text
            return True
        
        # Check for null bytes (common in binary files)
        if b'\x00' in sample:
            return False
        
        # Try to decode as UTF-8
        try:
            sample.decode('utf-8')
            return True
        except UnicodeDecodeError:
            pass
        
        # Try other common encodings
        for encoding in ['latin-1', 'cp1252', 'iso-8859-1', 'utf-16', 'utf-32', 'gbk', 'gb2312']:
            try:
                sample.decode(encoding)
                return True
            except UnicodeDecodeError:
                continue
        
        return False
    except (OSError, IOError):
        return False


@dataclass
class FileSnapshot:
    """Snapshot of a file's state"""
    path: str  # Relative path from working_dir
    original_hash: Optional[str]  # MD5 hash of content, None if file didn't exist
    current_hash: Optional[str]  # MD5 hash of content, None if file doesn't exist
    last_timestamp: float


class FileWatcher:
    """
    Watches a directory for file changes using watchfiles.
    
    Accumulates file changes and supports smart merging to detect files
    that were modified and then reverted to their original state.
    Tracks the original state of files when first changed, allowing detection
    of files that were modified and then reverted to their original state.
    """
    
    def __init__(self, working_dir: str):
        """
        Initialize the file watcher.
        
        Args:
            working_dir: Directory to watch
        """
        self.working_dir = os.path.abspath(working_dir)
        
        # Watch task state
        self._watch_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # Accumulator state
        self._pending_changes: Dict[str, FileSnapshot] = {}  # path -> snapshot
        self._lock = asyncio.Lock()
        self._ignore_edits: Dict[str, FileSnapshot] = {}     # agent edits should be ignored
        
        logger.debug(f"FileWatcher initialized for {self.working_dir}")

    # ==================== Accumulator Methods ====================

    async def add_ignore_edit(self, file_path: str, file_content: str) -> None:
        """
        Add a file to the ignore list for agent edits.
        
        Args:
            file_path: Absolute path to the file
            file_content: Content of the file
        """
        content_hash = _compute_content_hash(file_content)
        path = os.path.relpath(file_path, self.working_dir)
        # overwrite if already exists
        async with self._lock:
            self._ignore_edits[path] = FileSnapshot(
                path, original_hash=None, current_hash=content_hash, last_timestamp=0.0)

    async def record_change(self, abs_path: str, change_type: Change, timestamp: float) -> None:
        """
        Record a file change event.
        
        Args:
            abs_path: Absolute path to the changed file
            change_type: Type of change
            timestamp: When the change occurred
        """
        # For added and modified files, check file size and text encoding
        if change_type != Change.deleted:
            # Check if file exists
            if not os.path.exists(abs_path):
                return
            
            # Check file size
            try:
                file_size = os.path.getsize(abs_path)
                if file_size > MAX_FILE_SIZE:
                    logger.debug(f"File {abs_path} exceeds MAX_FILE_SIZE ({file_size} > {MAX_FILE_SIZE}), skipping")
                    return
            except OSError:
                return
            
            # Check if it's a text file
            if not _is_text_file(abs_path):
                logger.debug(f"File {abs_path} is not a text file, skipping")
                return
        
        rel_path = os.path.relpath(abs_path, self.working_dir)
        current_hash = _compute_file_hash(abs_path)

        async with self._lock:
            if rel_path in self._ignore_edits and self._ignore_edits[rel_path].current_hash == current_hash:
                logger.debug(f"File {rel_path} is an ignore edit, skipping")
                self._ignore_edits.pop(rel_path)
                return

            if rel_path in self._pending_changes:
                self._pending_changes[rel_path].current_hash = current_hash
                self._pending_changes[rel_path].last_timestamp = timestamp
            else:
                self._pending_changes[rel_path] = FileSnapshot(
                    path=rel_path,
                    original_hash=uuid.uuid4().hex if change_type != Change.added else None,      # TODO: Can not obtain original hash for modified files
                    current_hash=current_hash,
                    last_timestamp=timestamp
                )
        logger.debug(f"Recorded {change_type.value} for {rel_path}")

    async def merge_and_flush(self) -> List[FileChange]:
        """
        Merge accumulated changes and flush the buffer.
        
        Files that have been modified and then reverted to their original
        state will be excluded from the result.
        
        Returns:
            List of merged FileChange objects
        """
        async with self._lock:
            if not self._pending_changes:
                return []
            
            result: List[FileChange] = []
            
            for rel_path, snapshot in self._pending_changes.items():
                abs_path = os.path.join(self.working_dir, rel_path)
                
                # Determine final state
                current_hash = snapshot.current_hash
                
                # Check if file has effectively changed from original
                original_hash = snapshot.original_hash
                
                if current_hash == original_hash:
                    # File reverted to original state, skip
                    logger.debug(f"File {rel_path} reverted to original, skipping")
                    continue
                
                # Determine the effective change type
                if original_hash is None and current_hash is not None:
                    # File was created (didn't exist originally, exists now)
                    effective_type = Change.added
                elif original_hash is not None and current_hash is None:
                    # File was deleted (existed originally, doesn't exist now)
                    effective_type = Change.deleted
                else:
                    # File was modified
                    effective_type = Change.modified
                
                # Use the latest timestamp from the changes
                latest_timestamp = snapshot.last_timestamp
                
                result.append(FileChange(
                    path=rel_path,
                    path_absolute=abs_path,
                    change_type=effective_type,
                    timestamp=latest_timestamp,
                ))
            
            # Clear the buffers
            self._pending_changes.clear()
            
            logger.info(f"Merged and flushed {len(result)} file changes")
            return result
    
    def has_pending_changes(self) -> bool:
        """Check if there are any pending changes"""
        return len(self._pending_changes) > 0
    
    @property
    def pending_count(self) -> int:
        """Get the number of files with pending changes"""
        return len(self._pending_changes)

    # ==================== Watcher Methods ====================

    async def _watch_loop(self) -> None:
        """Main watch loop running in background
        Args:
            force_polling: Whether to force polling
            poll_delay_ms: Delay in milliseconds between polling
        """
        
        logger.info(f"Starting file watcher for {self.working_dir}")
        
        try:
            async for changes in awatch(
                self.working_dir,
                watch_filter=WatcherFilter(),
                stop_event=self._stop_event,
                recursive=True,
                ignore_permission_denied=True,
            ):
                current_time = time.time()
                
                for change_type, path in changes:
                    await self.record_change(
                        abs_path=path,
                        change_type=change_type,
                        timestamp=current_time
                    )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error in file watcher: {e}", exc_info=True)
        finally:
            logger.info(f"File watcher stopped for {self.working_dir}")
    
    async def start(self) -> None:
        """Start watching for file changes"""
        if self._watch_task is not None and not self._watch_task.done():
            logger.warning("File watcher already running")
            return
        
        self._stop_event.clear()
        self._watch_task = asyncio.create_task(self._watch_loop())
        logger.info(f"File watcher started for {self.working_dir}")
    
    async def stop(self) -> None:
        """Stop watching for file changes"""
        if self._watch_task is None or self._watch_task.done():
            logger.debug("File watcher not running")
            return
        
        logger.info("Stopping file watcher...")
        self._stop_event.set()
        
        try:
            # Wait for the task to complete with a timeout
            await asyncio.wait_for(self._watch_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("File watcher stop timed out, cancelling...")
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
        except asyncio.CancelledError:
            pass
        
        self._watch_task = None
        logger.info("File watcher stopped")
    
    def is_running(self) -> bool:
        """Check if the watcher is currently running"""
        return self._watch_task is not None and not self._watch_task.done()
