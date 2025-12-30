"""
WebFetch tool for fetching and processing web content using Tavily and Claude
"""
import os
import time
import hashlib
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from ..base_tool import BaseTool
from ..tool_names import ToolName
from tavily import TavilyClient
import anthropic


class WebFetchTool(BaseTool):
    """Tool for fetching web content and processing it with AI"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.WEB_FETCH
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "format": "uri",
                    "description": "The URL to fetch content from"
                },
                "prompt": {
                    "type": "string",
                    "description": "The prompt to run on the fetched content"
                }
            },
            "required": ["url", "prompt"],
            "additionalProperties": False
        }
