"""
WebSearch tool for searching the web using Tavily API
"""
import os
import json
from typing import Dict, Any, List, Optional
from ..base_tool import BaseTool
from ..tool_names import ToolName
from tavily import TavilyClient
import anthropic


class WebSearchTool(BaseTool):
    """Tool for searching the web using Tavily API"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.WEB_SEARCH
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 2,
                    "description": "The search query to use"
                },
                "allowed_domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Only include search results from these domains"
                },
                "blocked_domains": {
                    "type": "array", 
                    "items": {"type": "string"},
                    "description": "Never include search results from these domains"
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
