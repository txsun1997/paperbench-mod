"""
MemoryFetch tool for querying and extracting information from stored task execution trajectories
"""
from typing import Dict, Any
from ..base_tool import BaseTool
from ..tool_names import ToolName


class MemoryFetchTool(BaseTool):
    """Tool for fetching and querying information from historical task execution trajectories"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.MEMORY_FETCH
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query describing what information you want to extract from the context"
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }
