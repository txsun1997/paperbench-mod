"""
LS tool for listing files and directories
"""
import os
import glob
from typing import Dict, Any, List
from ..base_tool import BaseTool
from ..tool_names import ToolName


class LSTool(BaseTool):
    """Tool for listing files and directories"""
    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.LS
    
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
