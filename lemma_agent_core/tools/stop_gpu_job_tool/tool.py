"""
Stop GPU Job Tool - Stops a running distributed GPU training job
"""
from typing import Dict, Any
from ..base_tool import BaseTool
from ..tool_names import ToolName


class StopGPUJobTool(BaseTool):
    """Tool for stopping a running or pending GPU training job"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.STOP_GPU_JOB
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "The unique identifier of the GPU job to stop (returned when the job was created)"
                },
                "reason": {
                    "type": "string",
                    "description": "Optional reason for stopping the job (e.g., 'poor training metrics', 'incorrect configuration', 'user requested'). This helps with tracking and debugging."
                }
            },
            "required": ["job_id"],
            "additionalProperties": False
        }

