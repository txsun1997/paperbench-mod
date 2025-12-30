"""
Create GPU Job Tool - Creates a distributed GPU training job
"""
from typing import Dict, Any
from ..base_tool import BaseTool
from ..tool_names import ToolName


class CreateGPUJobTool(BaseTool):
    """Tool for creating distributed GPU training jobs on the GPU cluster"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.CREATE_GPU_JOB
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the GPU training job (must be unique and descriptive)"
                },
                "gpu_count": {
                    "type": "integer",
                    "enum": [1, 2, 4, 8],
                    "description": "Number of GPUs per instance. Must be exactly 1, 2, 4, or 8."
                },
                "instance_count": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 8,
                    "description": "Number of GPU instances to use (1-8). If instance_count is greater than 1, the gpu_count will be forced to 8."
                },
                "command": {
                    "type": "string",
                    "description": "Bash command to execute on the GPU cluster. CRITICAL: Must use absolute paths (e.g., 'sh /workspace/train.sh' NOT 'sh train.sh'). All file paths within the bash script must also be absolute. The command will run in the shared working directory accessible by both CPU and GPU servers."
                }
            },
            "required": ["name", "gpu_count", "instance_count", "command"],
            "additionalProperties": False
        }

