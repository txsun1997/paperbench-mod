"""
UpdatePlan tool for reading, editing, and writing the task execution plan
"""
from typing import Dict, Any
from ..base_tool import BaseTool
from ..tool_names import ToolName


class UpdatePlanTool(BaseTool):
    """Tool for managing the current task plan stored in the backend"""

    def __init__(self):
        super().__init__()

    @property
    def name(self) -> str:
        return ToolName.UPDATE_PLAN

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["read", "edit", "write"],
                    "description": "The operation to perform: 'read', 'edit', or 'write'. Only one operation is allowed at a time.",
                },
                "new_plan": {
                    "type": "string",
                    "description": "Required for 'write'. The complete new plan content.",
                },
                "old_string": {
                    "type": "string",
                    "description": "Required for 'edit'. The exact text to find and replace in the plan.",
                },
                "new_string": {
                    "type": "string",
                    "description": "Required for 'edit'. The replacement text for the old string.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        }

