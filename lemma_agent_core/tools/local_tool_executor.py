"""
Simplified tool executor for local agent operation.

Integrates tool definitions with their handlers for direct execution.
Uses real handlers from lemma-toolkit.
"""

import sys
import os
from typing import Dict, Any
from monitor import AgentLogger

# Add handlers directory to Python path
handlers_dir = os.path.join(os.path.dirname(__file__), 'handlers')
if handlers_dir not in sys.path:
    sys.path.insert(0, handlers_dir)

# Import tool handlers from toolkit
from bash_tool import BashToolHandler
from read_tool import ReadToolHandler
from write_tool import WriteToolHandler
from edit_tool import EditToolHandler
from ls_tool import LSToolHandler
from glob_tool import GlobToolHandler
from grep_tool import GrepToolHandler
from bash_output_tool import BashOutputToolHandler
from kill_bash_tool import KillBashToolHandler
from ls_bash_tool import LSBashToolHandler
from tool_state import ToolState


class LocalToolExecutor:
    """
    Executes tools locally by directly calling their handlers.
    
    Replaces the complex ToolService/RemoteToolHandler architecture
    with simple direct execution.
    """
    
    def __init__(self, working_dir: str, task_id: str):
        self.logger = AgentLogger(task_id=task_id)
        self.tool_state = ToolState(task_id=task_id, working_dir=working_dir)
        
        # Initialize tool handlers
        self.handlers = {
            "Bash": BashToolHandler(self.tool_state),
            "Read": ReadToolHandler(self.tool_state),
            "Write": WriteToolHandler(self.tool_state),
            "Edit": EditToolHandler(self.tool_state),
            "LS": LSToolHandler(self.tool_state),
            "Glob": GlobToolHandler(self.tool_state),
            "Grep": GrepToolHandler(self.tool_state),
            "BashOutput": BashOutputToolHandler(self.tool_state),
            "KillBash": KillBashToolHandler(self.tool_state),
            "LSBash": LSBashToolHandler(self.tool_state),
        }
        
        self.logger.info(f"Initialized LocalToolExecutor with {len(self.handlers)} tool handlers")
    
    async def execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool with the given input.
        
        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool
            
        Returns:
            Dict with execution result:
            - success: bool
            - result: str (tool output)
            - display_result: dict with display information
            - error: str (if failed)
        """
        if tool_name not in self.handlers:
            error_msg = f"Unknown tool: {tool_name}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "result": error_msg,
                "display_result": {
                    "type": "text",
                    "data": {},
                    "tool_success": False,
                    "error": error_msg
                },
                "error": error_msg
            }
        
        handler = self.handlers[tool_name]
        
        try:
            self.logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
            result = await handler.execute(tool_input)
            self.logger.info(f"Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            error_msg = f"Error executing {tool_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "result": error_msg,
                "display_result": {
                    "type": "text",
                    "data": {},
                    "tool_success": False,
                    "error": error_msg
                },
                "error": error_msg
            }
    
    async def cleanup(self):
        """Cleanup tool state and resources"""
        if self.tool_state:
            await self.tool_state.terminate()
