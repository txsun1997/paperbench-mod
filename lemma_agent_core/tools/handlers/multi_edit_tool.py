"""
MultiEdit Tool - Makes multiple edits to a single file in one operation
"""
import os
from typing import Dict, Any, List, Optional
from base_tool_handler import BaseToolHandler, ToolState, ToolFailedError
from diff_utils import generate_diff_data
from tool_categories import ToolName


class MultiEditToolHandler(BaseToolHandler):
    """Tool for making multiple edits to a single file in one operation"""
    
    def __init__(self, tool_state: ToolState):
        super().__init__(tool_state=tool_state)
        self.requires_confirmation = True
    
    @property
    def name(self) -> str:
        return ToolName.MULTI_EDIT
    
    @property
    def display_result_type(self) -> str:
        return "edit_result"

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file to modify"
                },
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "old_string": {
                                "type": "string",
                                "description": "The text to replace"
                            },
                            "new_string": {
                                "type": "string",
                                "description": "The text to replace it with"
                            },
                            "replace_all": {
                                "type": "boolean",
                                "default": False,
                                "description": "Replace all occurences of old_string (default false)."
                            }
                        },
                        "required": ["old_string", "new_string"],
                        "additionalProperties": False
                    },
                    "minItems": 1,
                    "description": "Array of edit operations to perform sequentially on the file"
                }
            },
            "required": ["file_path", "edits"],
            "additionalProperties": False,
            "$schema": "http://json-schema.org/draft-07/schema#"
        }
    
    async def execute_async(self, file_path: str, edits: List[Dict[str, Any]], update_file: bool = True) -> Dict[str, Any]:
        """Execute the tool"""
        # Validate absolute path
        if not os.path.isabs(file_path):
            raise ToolFailedError(f"Error: file_path must be an absolute path, got: {file_path}")
        
        # Validate edits array
        if not edits:
            raise ToolFailedError("Error: edits array cannot be empty")
        
        # Validate each edit
        for i, edit in enumerate(edits):
            if not isinstance(edit, dict):
                raise ToolFailedError(f"Error: edit {i+1} must be an dictionary")
            
            if "old_string" not in edit:
                raise ToolFailedError(f"Error: edit {i+1} missing required field 'old_string'")
            
            if "new_string" not in edit:
                raise ToolFailedError(f"Error: edit {i+1} missing required field 'new_string'")
            
            if edit["old_string"] == edit["new_string"]:
                raise ToolFailedError(f"Error: edit {i+1} old_string and new_string cannot be the same")
            
            if not edit["old_string"]:
                raise ToolFailedError(f"Error: edit {i+1} old_string cannot be empty")
        
        # Editing existing file
        if not os.path.exists(file_path):
            raise ToolFailedError(f"Error: File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ToolFailedError(f"Error: Path is not a file: {file_path}")
        
        # Check if file has been read first and the read is still fresh
        if not self.is_file_read_fresh(file_path):
            if not self.is_file_read(file_path):
                raise ToolFailedError(f"Error: You must read the file's contents before editing: {file_path}")
            else:
                raise ToolFailedError(f"Error: The file {file_path} has been modified since it was last read. Please read the file again before editing.")
        
        try:
            # Read the existing file
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # Backup the original content before any modifications (only if update_file=True)
            if update_file:
                self.backup_file_state(file_path, current_content)
            
            # 保存原始内容，用于后续生成diff
            original_content = current_content
        except PermissionError:
            raise ToolFailedError(f"Error: Permission denied reading file: {file_path}")
        except UnicodeDecodeError:
            raise ToolFailedError(f"Error: File appears to be binary or has encoding issues: {file_path}")
        
        applied_edits = []
        remaining_edits = edits
        
        # Apply each edit sequentially
        try:
            for i, edit in enumerate(remaining_edits):
                old_string = edit["old_string"]
                new_string = edit["new_string"]
                replace_all = edit.get("replace_all", False)
                
                # Check if old_string exists in current content
                if old_string not in current_content:
                    raise ToolFailedError(f"Error: edit {i+1+len(applied_edits)} old_string not found in current content: {old_string}")
                
                # For non-replace_all operations, check uniqueness
                if not replace_all:
                    occurrences = current_content.count(old_string)
                    if occurrences > 1:
                        raise ToolFailedError(f"Error: edit {i+1+len(applied_edits)} old_string appears {occurrences} times. Either provide a larger string with more surrounding context to make it unique or use replace_all=true.")
                
                # Perform the replacement
                if replace_all:
                    # Replace all occurrences - no count limit
                    current_content = current_content.replace(old_string, new_string)
                    applied_edits.append(f'Replaced all occurrences of "{old_string}" with "{new_string}"')
                else:
                    # Replace only first occurrence
                    current_content = current_content.replace(old_string, new_string, 1)
                    applied_edits.append(f'Replaced first occurrence of "{old_string}" with "{new_string}"')
            
            if update_file:
                # Write the final content to file
                await self.tool_state.write_file(file_path, current_content)
            
            # Format the summary in the requested format
            total_edits = len(applied_edits)
            
            summary = f"Applied {total_edits} edit{'s' if total_edits != 1 else ''} to {file_path}:\n"
            for i, edit in enumerate(applied_edits, 1):
                summary += f"{i}. {edit}\n"
            
            # Generate diff data for display
            diff_data = self._generate_diff_data(original_content, current_content, file_path)
            
            return {
                'tool_success': True,
                'result': summary.rstrip(),
                'display_result': diff_data
            }
            
        except PermissionError:
            raise ToolFailedError(f"Error: Permission denied writing to file: {file_path}")
        except Exception as e:
            raise ToolFailedError(f"Error applying edits to file {file_path}: {str(e)}")
    
    def _generate_diff_data(self, old_content, new_content, filename):
        """Generate diff data for display"""
        difftext = generate_diff_data(
            old_content=old_content,
            new_content=new_content)
        return {
            'old_file': filename,
            'new_file': filename,
            'diff': difftext
        }
