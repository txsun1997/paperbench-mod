"""
Simplified diff utilities for tool handlers
Extracted from support_utils.py to avoid external dependencies
"""
import difflib
from typing import Dict, Any


def generate_diff_data(old_content: str, new_content: str, file_path: str = "") -> Dict[str, Any]:
    """
    Generate unified diff between old and new content
    
    Args:
        old_content: Original file content
        new_content: Modified file content
        file_path: Path to the file (for display purposes)
        
    Returns:
        Dict with diff data including unified diff string
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm=""
    )
    
    diff_str = '\n'.join(diff)
    
    return {
        "diff": diff_str,
        "old_lines": len(old_lines),
        "new_lines": len(new_lines),
    }
