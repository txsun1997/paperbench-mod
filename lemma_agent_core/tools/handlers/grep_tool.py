"""
Grep tool for powerful text search using ripgrep
"""
import os
import subprocess
from typing import Dict, Any, Optional
from base_tool_handler import BaseToolHandler, ToolState, ToolFailedError
from tool_categories import ToolName

class GrepToolHandler(BaseToolHandler):
    """Tool for powerful text search using ripgrep"""
    
    @property
    def name(self) -> str:
        return ToolName.GREP
    
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
                    "description": "The regular expression pattern to search for in file contents"
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search in (rg PATH). Defaults to current working directory."
                },
                "glob": {
                    "type": "string",
                    "description": "Glob pattern to filter files (e.g. \"*.js\", \"*.{ts,tsx}\") - maps to rg --glob"
                },
                "output_mode": {
                    "type": "string",
                    "enum": ["content", "files_with_matches", "count"],
                    "description": "Output mode: \"content\" shows matching lines (supports -A/-B/-C context, -n line numbers, head_limit), \"files_with_matches\" shows file paths (supports head_limit), \"count\" shows match counts (supports head_limit). Defaults to \"files_with_matches\"."
                },
                "-B": {
                    "type": "number",
                    "description": "Number of lines to show before each match (rg -B). Requires output_mode: \"content\", ignored otherwise."
                },
                "-A": {
                    "type": "number",
                    "description": "Number of lines to show after each match (rg -A). Requires output_mode: \"content\", ignored otherwise."
                },
                "-C": {
                    "type": "number",
                    "description": "Number of lines to show before and after each match (rg -C). Requires output_mode: \"content\", ignored otherwise."
                },
                "-n": {
                    "type": "boolean",
                    "description": "Show line numbers in output (rg -n). Requires output_mode: \"content\", ignored otherwise."
                },
                "-i": {
                    "type": "boolean",
                    "description": "Case insensitive search (rg -i)"
                },
                "type": {
                    "type": "string",
                    "description": "File type to search (rg --type). Common types: js, py, rust, go, java, etc. More efficient than include for standard file types."
                },
                "head_limit": {
                    "type": "number",
                    "description": "Limit output to first N lines/entries, equivalent to \"| head -N\". Works across all output modes: content (limits output lines), files_with_matches (limits file paths), count (limits count entries). When unspecified, shows all results from ripgrep."
                },
                "multiline": {
                    "type": "boolean",
                    "description": "Enable multiline mode where . matches newlines and patterns can span lines (rg -U --multiline-dotall). Default: false."
                }
            },
            "required": ["pattern"],
            "additionalProperties": False
        }
    
    async def execute_async(self, pattern: str, path: Optional[str] = None, 
                          glob: Optional[str] = None, output_mode: str = "files_with_matches",
                          **kwargs) -> Dict[str, Any]:
        """Execute the Grep tool using ripgrep"""
        # Handle parameters with hyphens in their names
        context_before = kwargs.get("-B")
        context_after = kwargs.get("-A") 
        context_around = kwargs.get("-C")
        line_numbers = kwargs.get("-n", False)
        case_insensitive = kwargs.get("-i", False)
        file_type = kwargs.get("type")
        head_limit = kwargs.get("head_limit")
        multiline_mode = kwargs.get("multiline", False)
        
        # Save session working directory for display methods
        # This is captured during execute_async when the working directory is correct
        self._execution_working_dir = self.tool_state.get_working_dir()
        
        if not pattern.strip():
            raise ToolFailedError("Error: pattern parameter cannot be empty")
        
        # Use ripgrep command resolved during service initialization
        rg_command = os.environ.get("LEMMA_RG_PATH")
        if not rg_command:
            raise ToolFailedError(
                "Error: ripgrep (rg) not available. Please install ripgrep and restart the Lemma service, "
                "or set LEMMA_RG_PATH to the rg executable."
            )
        
        # Build ripgrep command
        cmd = [rg_command]
        
        # Add pattern
        cmd.append(pattern)
        
        # Add path - either specified or current working directory
        search_path = path or self._execution_working_dir
        if not os.path.exists(search_path):
            raise ToolFailedError(f"Error: Path does not exist: {search_path}")
        cmd.append(search_path)
        
        # Set output mode
        if output_mode == "files_with_matches":
            cmd.append("--files-with-matches")
        elif output_mode == "count":
            cmd.append("--count")
        # For content mode, no special flag needed (default behavior)
        
        # Add optional parameters
        if case_insensitive:
            cmd.append("--ignore-case")
        
        if multiline_mode:
            cmd.extend(["--multiline", "--multiline-dotall"])
        
        if glob:
            cmd.extend(["--glob", glob])
        
        if file_type:
            cmd.extend(["--type", file_type])
        
        # Context options (only for content mode)
        if output_mode == "content":
            if line_numbers:
                cmd.append("--line-number")
            
            if context_after is not None:
                cmd.extend(["-A", str(int(context_after))])
            
            if context_before is not None:
                cmd.extend(["-B", str(int(context_before))])
            
            if context_around is not None:
                cmd.extend(["-C", str(int(context_around))])
        
        try:
            # Execute ripgrep
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                output = result.stdout.strip()
                
                if not output:
                    search_location = path or "current directory"
                    raise ToolFailedError(f"No matches found for pattern '{pattern}' in {search_location}")
                
                # Apply head_limit if specified
                if head_limit is not None:
                    head_limit = int(head_limit)  # Ensure it's an integer
                    lines = output.split('\n')
                    if len(lines) > head_limit:
                        output = '\n'.join(lines[:head_limit])
                        output += f"\n... (showing first {head_limit} of {len(lines)} results)"
                
                # Format output based on mode
                search_location = path or self._execution_working_dir
                if output_mode == "files_with_matches":
                    line_count = len(output.split('\n'))
                    result_text = f"Found matches in {line_count} files for pattern '{pattern}' in {search_location}:\n\n{output}"
                elif output_mode == "count":
                    result_text = f"Match counts for pattern '{pattern}' in {search_location}:\n\n{output}"
                else:  # content mode
                    result_text = f"Search results for pattern '{pattern}' in {search_location}:\n\n{output}"
                
                # Apply character length limit (30000 characters like ls_tool and glob_tool)
                if len(result_text) > 30000:
                    result_text = result_text[:30000] + "\n... (truncated due to length)"

                if path:
                    self.mark_file_as_read(path)
                
                return {
                    'tool_success': True,
                    'result': result_text,
                    'display_result': {
                        'text': result_text
                    }
                }
                
            elif result.returncode == 1:
                # No matches found
                search_location = path or self._execution_working_dir
                result_text = f"No matches found for pattern '{pattern}' in {search_location}"
                if path:
                    self.mark_file_as_read(path)
                return {
                    'tool_success': True,
                    'result': result_text,
                    'display_result': {
                        'text': result_text
                    }
                }
            else:
                # Error occurred
                error_msg = result.stderr.strip() or "Unknown error occurred"
                raise ToolFailedError(f"Error executing ripgrep: {error_msg}")
                
        except subprocess.TimeoutExpired:
            raise ToolFailedError(f"Error: Search timed out after 30 seconds. Pattern '{pattern}' may be too complex or search space too large.")

        except Exception as e:
            raise ToolFailedError(f"Error executing Grep tool: {str(e)}")
