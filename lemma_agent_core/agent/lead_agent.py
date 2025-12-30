from datetime import datetime
import os
import platform
from typing import Dict, Any

from .base_agent import BaseAgent
from config import AgentsConfig
from utils.prompt_utils import load_prompt_template
from utils.skill_utils import get_available_skills_prompt


class LeadAgent(BaseAgent):
    """
    Lead Agent - simplified for local operation.
    
    Removed dependencies on:
    - RemoteMessageService
    - backend system_info
    - toolkit_extend_attributes
    """
    
    def __init__(
        self, 
        agents_config: AgentsConfig, 
        working_dir: str,
        task_id: str = None
    ):
        super().__init__(agents_config, working_dir=working_dir, task_id=task_id)
        
        # Load prompt templates
        self.sys_identity = load_prompt_template('sys_identity.md')
        self.sys_code_agent = load_prompt_template('sys_code_agent.md')
        self._base_prompt = self.sys_identity + '\n\n' + self.sys_code_agent
        
        self.sys_skills = load_prompt_template('sys_skills.md')
        
        # Initialize system prompt
        self._initialize_system_prompt()
        
        self.logger.info(f"[TOOLS] Loaded {len(self.tools)} tools: {', '.join([tool.get('name') for tool in self.tools])}")
    
    def _initialize_system_prompt(self) -> None:
        """Initialize the system prompt with system status information"""
        # Get basic system info locally
        working_dir = os.path.abspath(self.working_dir)
        is_git_repo = os.path.exists(os.path.join(working_dir, '.git'))
        system_platform = platform.platform()
        system_release = platform.release()
        local_date = datetime.now().strftime('%Y-%m-%d')
        
        env_info = f"""<env>
        Working directory: {working_dir}
        Is directory a git repo: {is_git_repo}
        Platform: {system_platform}
        System release: {system_release}
        Timezone: Local
        Today's date: {local_date}
        </env>
        """
        
        self._system_prompt = self._base_prompt.replace('<env></env>', env_info)
        
        # Add skills system prompt
        available_skills = get_available_skills_prompt()
        self._system_prompt += "\n\n" + self.sys_skills.replace('<available_skills></available_skills>', available_skills)
        
        # Add git status if available
        if is_git_repo:
            try:
                import subprocess
                git_status = subprocess.check_output(['git', 'status', '--short'], cwd=working_dir).decode('utf-8')
                current_branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=working_dir).decode('utf-8').strip()
                
                git_section = f"""
Current branch: {current_branch}
Git status:
{git_status}
"""
                self._system_prompt += "\n\n# Git Status\n\n" + git_section
            except Exception as e:
                self.logger.warning(f"Failed to get git status: {e}")
