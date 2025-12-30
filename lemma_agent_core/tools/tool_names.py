"""
Tool Names Enum - Centralized registry of all tool names for easy maintenance
"""
from enum import Enum


class ToolName(str, Enum):
    """Enum containing all available tool names in the system"""

    # File operations
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
    # MULTI_EDIT = "MultiEdit"

    # Search and navigation
    GLOB = "Glob"
    GREP = "Grep"
    LS = "LS"

    # Bash operations
    BASH = "Bash"
    BASH_OUTPUT = "BashOutput"
    KILL_BASH = "KillBash"
    LS_BASH = "LSBash"

    # Web operations
    WEB_FETCH = "WebFetch"
    WEB_SEARCH = "WebSearch"

    # AI and research tools
    ANNA = "AnnaResearch"

    # Memory and state management
    MEMORY_FETCH = "MemoryFetch"
    TODO_WRITE = "TodoWrite"
    UPDATE_PLAN = "UpdatePlan"

    # Mode control
    # EXIT_MODE = "ExitMode"
    # EXIT_PLAN_MODE = "ExitPlanMode"
    # PHASE_CONTROLLER = "PhaseController"

    # GPU operations
    CREATE_GPU_JOB = "CreateGPUJob"
    VIEW_GPU_JOB = "ViewGPUJob"
    STOP_GPU_JOB = "StopGPUJob"

    # Skills
    VIEW_SKILLS = "ViewSkills"

    def __str__(self) -> str:
        """Return the string value of the enum"""
        return self.value
