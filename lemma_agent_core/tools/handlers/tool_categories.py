"""
Tool Categories Configuration for Interrupt Handling
====================================================

This module defines the categorization of all remote tools for interrupt handling.

Tool Categories:
- 'edit': Edit-type tools (Edit, MultiEdit, Write) - wait for completion when interrupted
- 'readonly': Read-only tools (Read, Grep, Glob, LSTool, LSBashTool) - directly interrupt
- 'bash': Bash execution tool - send interrupt signal but keep session alive
- 'bash_output': BashOutput tool - end execution without updating read pointer
- 'kill_bash': KillBash tool - wait for completion when interrupted
"""

from enum import Enum


class ToolName(str, Enum):
    """Enum containing all available tool names in the system"""

    # File operations
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
    MULTI_EDIT = "MultiEdit"

    # Search and navigation
    GLOB = "Glob"
    GREP = "Grep"
    LS = "LS"

    # Bash operations
    BASH = "Bash"
    BASH_OUTPUT = "BashOutput"
    KILL_BASH = "KillBash"
    LS_BASH = "LSBash"

    def __str__(self) -> str:
        return self.value


from typing import Dict

# Tool name to category mapping
TOOL_CATEGORIES: Dict[str, str] = {
    # Edit-type tools - wait for completion
    ToolName.EDIT: 'edit',
    ToolName.MULTI_EDIT: 'edit',
    ToolName.WRITE: 'edit',

    # Read-only tools - direct interrupt
    ToolName.READ: 'readonly',
    ToolName.GREP: 'readonly',
    ToolName.GLOB: 'readonly',
    ToolName.LS: 'readonly',
    ToolName.LS_BASH: 'readonly',

    # Bash execution - send interrupt signal, keep session
    ToolName.BASH: 'bash',

    # BashOutput - end execution, don't update pointer
    ToolName.BASH_OUTPUT: 'bash_output',

    # KillBash - wait for completion
    ToolName.KILL_BASH: 'kill_bash',
}


def get_tool_category(tool_name: str) -> str:
    """Get the category for a given tool name.

    Args:
        tool_name: Name of the tool

    Returns:
        Category string, defaults to 'readonly' if tool not found
    """
    return TOOL_CATEGORIES.get(tool_name, 'readonly')


def is_waitable_tool(tool_name: str) -> bool:
    """Check if a tool should wait for completion when interrupted.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool should wait for completion (edit, kill_bash), False otherwise
    """
    category = get_tool_category(tool_name)
    return category in ('edit', 'kill_bash')


def is_interruptible_tool(tool_name: str) -> bool:
    """Check if a tool can be directly interrupted.

    Args:
        tool_name: Name of the tool

    Returns:
        True if tool can be directly interrupted (readonly, bash_output), False otherwise
    """
    category = get_tool_category(tool_name)
    return category in ('readonly', 'bash_output', 'bash', 'edit')
