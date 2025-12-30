"""
Anna tool for deep research using Anna API
"""
from typing import Dict, Any
from ..base_tool import BaseTool
from ..tool_names import ToolName


class AnnaTool(BaseTool):
    """Tool for performing deep research using Anna API"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.ANNA
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 20,
                    "description": "The detailed research query or question to investigate"
                }
            },
            "required": ["query"],
            "additionalProperties": False
        }

