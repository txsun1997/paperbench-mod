"""
View GPU Job Tool - Checks the status of a distributed GPU training job
"""
from typing import Dict, Any
from ..base_tool import BaseTool
from ..tool_names import ToolName


class ViewGPUJobTool(BaseTool):
    """Tool for viewing the status and details of a GPU training job"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.VIEW_GPU_JOB
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "The unique identifier of the GPU job to check (returned when the job was created)"
                }
            },
            "required": ["job_id"],
            "additionalProperties": False
        }

