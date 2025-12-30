"""
Glob tool for fast file pattern matching
"""
import os
import glob
from typing import Dict, Any, Optional
from base_tool_handler import BaseToolHandler, ToolState, ToolFailedError
from tool_categories import ToolName
class GlobToolHandler(BaseToolHandler):
    """Tool for fast file pattern matching using glob patterns"""
    
    @property
    def name(self) -> str:
        return ToolName.GLOB
    
    @property
    def display_result_type(self) -> str:
        return "text_result"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The glob pattern to match files against"
                },
                "path": {
                    "type": "string",
                    "description": "The directory to search in. If not specified, the current working directory will be used. IMPORTANT: Omit this field to use the default directory. DO NOT enter \"undefined\" or \"null\" - simply omit it for the default behavior. Must be a valid absolute directory path if provided."
                }
            },
            "required": ["pattern"],
            "additionalProperties": False
        }
    
    async def execute_async(self, pattern: str, path: Optional[str] = None) -> Dict[str, Any]:
        """Execute the Glob tool"""
        # Save current working directory for display methods
        # This is captured during execute_async when the working directory is correct
        self._execution_working_dir = self.tool_state.get_working_dir()
        
        if not pattern.strip():
            raise ToolFailedError("Error: pattern parameter cannot be empty")
        
        # Determine search directory - use explicit path or session working directory
        search_dir = path or self._execution_working_dir
        
        if not os.path.exists(search_dir):
            raise ToolFailedError(f"Error: Path does not exist: {search_dir}")
        
        if not os.path.isdir(search_dir):
            raise ToolFailedError(f"Error: Path is not a directory: {search_dir}")
        

        
        try:
            # Change to search directory and perform glob search
            original_cwd = os.getcwd()
            os.chdir(search_dir)

            try:
                # Use glob to find matching files
                matches = glob.glob(pattern, recursive=True)
                
                # Convert to absolute paths and filter out directories
                file_matches = []
                for match in matches:
                    abs_path = os.path.abspath(match)
                    if os.path.isfile(abs_path):
                        file_matches.append(abs_path)
                
                # Sort by modification time (most recent first)
                file_matches.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                
            finally:
                # Always restore original working directory
                os.chdir(original_cwd)
        
            if not file_matches:
                agent_result = f"No files found matching pattern '{pattern}' in directory '{search_dir}'"
                return {
                    'tool_success': True,
                    'result': agent_result.strip(),
                    'display_result': {
                        'text': 'No files found'
                    }
                }
            
            # Format results for agent
            agent_result = f"Found {len(file_matches)} files matching pattern '{pattern}' in '{search_dir}':\n\n"
            for file_path in file_matches:
                agent_result += f"  {file_path}\n"
            
            agent_result = agent_result.strip()
            
            # Apply character length limit (30000 characters like ls_tool)
            if len(agent_result) > 30000:
                agent_result = agent_result[:30000] + "\n... (truncated due to length)"
            
            # Format results for display
            display_text = self._parse_glob_result(agent_result, pattern, path, full_output=True)
            
            return {
                'tool_success': True,
                'result': agent_result.strip(),
                'display_result': {
                    'text': display_text
                }
            }
        except Exception as e:
            raise ToolFailedError(f"Error executing glob pattern '{pattern}' in directory '{search_dir}': {str(e)}")
    
    def _parse_glob_result(self, result: str, pattern: str, path: str, full_output: bool = False) -> str:
        """解析Glob搜索结果"""
        lines = result.split('\n')
        
        # 提取实际的文件列表（跳过头部信息）
        result_lines = []
        found_header = False
        
        for line in lines:
            # 跳过头部信息行
            if not found_header:
                if "Found" in line and "files matching pattern" in line:
                    found_header = True
                    continue
                elif line.strip() == "":
                    continue
            else:
                # 找到头部后，收集所有非空行作为结果
                if line.strip():
                    # 移除缩进并清理格式
                    clean_line = line.strip()
                    if clean_line.startswith("  "):
                        clean_line = clean_line[2:]  # 移除前导空格
                    result_lines.append(clean_line)
        
        # 如果没有找到明确的头部，尝试从结果中提取文件路径
        if not result_lines and lines:
            # 查找包含文件路径的行（通常有缩进或者包含路径分隔符）
            for line in lines[1:]:  # 跳过第一行（通常是描述）
                if line.strip() and ("/" in line or "\\" in line):
                    clean_line = line.strip()
                    if clean_line.startswith("  "):
                        clean_line = clean_line[2:]
                    result_lines.append(clean_line)
        return '\n'.join(result_lines)
