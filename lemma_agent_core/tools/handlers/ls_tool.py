"""
LS tool for listing files and directories
"""
import os
import glob
from typing import Dict, Any, List, Optional
from base_tool_handler import BaseToolHandler, ToolState, ToolFailedError
from tool_categories import ToolName

class LSToolHandler(BaseToolHandler):
    """Tool for listing files and directories"""
    
    @property
    def name(self) -> str:
        return ToolName.LS
    
    @property
    def display_result_type(self) -> str:
        return "text_result"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute path to the directory to list (must be absolute, not relative)"
                },
                "ignore": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of glob patterns to ignore"
                }
            },
            "required": ["path"],
            "additionalProperties": False
        }
    
    async def execute_async(self, path: str, ignore: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute the LS tool"""
        
        # Validate that path is absolute
        if not os.path.isabs(path):
            raise ToolFailedError(f"Error: Path must be absolute, got: {path}")
        
        # Check if path exists
        if not os.path.exists(path):
            raise ToolFailedError(f"Error: Path does not exist: {path}")
        
        # Check if path is a directory
        if not os.path.isdir(path):
            raise ToolFailedError(f"Error: Path is not a directory: {path}")
        
        try:
            # List all items in directory
            items = os.listdir(path)
            items.sort()  # Sort for consistent output
            
            # Default ignore patterns - always applied
            default_ignore = [
                ".*",  # Hidden files/directories (starting with .)
                "__pycache__",  # Python cache
                "*.pyc",  # Python compiled files
                "*.pyo",  # Python optimized files
                "*.pyd",  # Python extension modules
                "node_modules",  # Node.js modules
                ".git",  # Git directory
                ".svn",  # SVN directory
                ".hg",  # Mercurial directory
                "*.swp",  # Vim swap files
                "*.swo",  # Vim swap files
                "*~",  # Backup files
                ".DS_Store",  # macOS metadata
                "Thumbs.db",  # Windows thumbnails
                ".vscode",  # VS Code settings
                ".idea",  # IntelliJ IDEA settings
                "*.egg-info",  # Python egg info
                ".tox",  # Tox testing
                ".coverage",  # Coverage files
                ".pytest_cache",  # Pytest cache
                ".mypy_cache",  # MyPy cache
            ]
            
            # Combine default ignore patterns with user-provided ones
            all_ignore_patterns = default_ignore[:]
            if ignore:
                all_ignore_patterns.extend(ignore)
            
            # Apply ignore patterns
            filtered_items = []
            for item in items:
                item_path = os.path.join(path, item)
                should_ignore = False
                
                for pattern in all_ignore_patterns:
                    if self._matches_pattern(item, pattern) or self._matches_pattern(item_path, pattern):
                        should_ignore = True
                        break
                
                if not should_ignore:
                    filtered_items.append(item)
            
            items = filtered_items
            
            if not items:
                success_message = f"Directory {path} is empty"
            else:
                # Format output in recursive tree-like structure
                result_lines = []
                self._build_tree_recursive(path, result_lines, "", ignore, depth=0, max_depth=1)
                success_message = "\n".join(result_lines)
            
            # Truncate result if it exceeds 30000 characters
            if len(success_message) > 30000:
                success_message = success_message[:30000] + "\n... (truncated due to length)"
            
            return {
                'tool_success': True,
                'result': success_message,
                'display_result': {
                    'text': success_message
                }
            }
            
        except PermissionError:
            raise ToolFailedError(f"Error: Permission denied accessing: {path}")
        except Exception as e:
            raise ToolFailedError(f"Error listing directory {path}: {str(e)}")
    
    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a name matches a glob pattern"""
        try:
            import fnmatch
            return fnmatch.fnmatch(name, pattern)
        except Exception:
            return False
    
    def _build_tree_recursive(self, current_path: str, result_lines: List[str], prefix: str, ignore: Optional[List[str]] = None, depth: int = 0, max_depth: int = 1) -> None:
        """Recursively build tree structure for directory listing
        
        Args:
            current_path: Current directory path
            result_lines: List to accumulate output lines
            prefix: Prefix string for indentation
            ignore: List of glob patterns to ignore
            depth: Current depth level (0 is root)
            max_depth: Maximum depth to traverse (1 means 2 layers total: 0 and 1)
        """
        try:
            # Add current directory to result
            dir_name = os.path.basename(current_path)
            if not dir_name:  # Root directory case
                dir_name = current_path
            result_lines.append(f"{prefix}- {dir_name}/")
            
            # Stop recursion if we've reached max depth
            if depth >= max_depth:
                return
            
            # Get items in current directory
            items = os.listdir(current_path)
            items.sort()
            
            # Default ignore patterns - always applied
            default_ignore = [
                ".*",  # Hidden files/directories (starting with .)
                "__pycache__",  # Python cache
                "*.pyc",  # Python compiled files
                "*.pyo",  # Python optimized files
                "*.pyd",  # Python extension modules
                "node_modules",  # Node.js modules
                ".git",  # Git directory
                ".svn",  # SVN directory
                ".hg",  # Mercurial directory
                "*.swp",  # Vim swap files
                "*.swo",  # Vim swap files
                "*~",  # Backup files
                ".DS_Store",  # macOS metadata
                "Thumbs.db",  # Windows thumbnails
                ".vscode",  # VS Code settings
                ".idea",  # IntelliJ IDEA settings
                "*.egg-info",  # Python egg info
                ".tox",  # Tox testing
                ".coverage",  # Coverage files
                ".pytest_cache",  # Pytest cache
                ".mypy_cache",  # MyPy cache
            ]
            
            # Combine default ignore patterns with user-provided ones
            all_ignore_patterns = default_ignore[:]
            if ignore:
                all_ignore_patterns.extend(ignore)
            
            # Apply ignore patterns
            filtered_items = []
            for item in items:
                item_path = os.path.join(current_path, item)
                should_ignore = False
                
                for pattern in all_ignore_patterns:
                    if self._matches_pattern(item, pattern) or self._matches_pattern(item_path, pattern):
                        should_ignore = True
                        break
                
                if not should_ignore:
                    filtered_items.append(item)
            
            items = filtered_items
            
            # Process each item
            for i, item in enumerate(items):
                item_path = os.path.join(current_path, item)
                is_last = (i == len(items) - 1)
                
                if os.path.isdir(item_path):
                    # Recursively process subdirectory
                    new_prefix = prefix + ("  " if is_last else "  ")
                    self._build_tree_recursive(item_path, result_lines, new_prefix, ignore, depth + 1, max_depth)
                else:
                    # Add file to result
                    result_lines.append(f"{prefix}  - {item}")
                    
        except PermissionError:
            result_lines.append(f"{prefix}  [Permission Denied]")
        except Exception:
            pass  # Skip directories that can't be accessed
