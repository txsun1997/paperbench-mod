"""
Read Tool - Reads files from the local filesystem
"""
import os
import mimetypes
import base64
import httpx
from urllib.parse import urlparse
from typing import Dict, Any
from ..base_tool import BaseTool
from ..tool_names import ToolName


class ReadTool(BaseTool):
    """Tool for reading files from the local filesystem"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.READ
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to read, or HTTP URL for PDF/image files"
                },
                "offset": {
                    "type": "number",
                    "description": "The line number to start reading from. Only provide if the file is too large to read at once"
                },
                "limit": {
                    "type": "number", 
                    "description": "The number of lines to read. Only provide if the file is too large to read at once."
                }
            },
            "required": ["file_path"],
            "additionalProperties": False
        }
