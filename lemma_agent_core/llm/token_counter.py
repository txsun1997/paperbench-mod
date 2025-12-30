import io
import json
import boto3
import base64
import httpx
import PyPDF2
from PIL import Image
from anthropic import AsyncAnthropic
from typing import Dict, Any, List, Optional
from monitor import AgentLogger
from config import TokenCountConfig

class TokenCounter:
    """Token counting functionality for various content types"""
    
    def __init__(self, token_count_config: Optional[TokenCountConfig] = None):
        self.token_count_config = token_count_config
        self.logger = AgentLogger()
        self.llm_client = boto3.client("bedrock-runtime", region_name=self.token_count_config.aws_region)

    async def count_tokens(
        self, 
        system_prompt: str, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        # num_previous_input_tokens: int = 0
        thinking_enabled: bool = False
    ) -> int:
        """
        统一的token计数方法，根据配置选择计数策略
        
        Args:
            system_prompt: 系统提示词
            messages: 消息列表
            tools: 工具列表
            thinking_enabled: 是否启用思考模式
        Returns:
            Token数量
        """
        # 从配置中获取计数方法
        count_method = self.token_count_config.method if self.token_count_config else "estimated"
        
        # 根据方法选择对应的计数策略
        if count_method == "accurate":
            try:
                return await self.accurate_token_count(system_prompt, messages, tools, thinking_enabled)
            except Exception as e:
                self.logger.error(f"[TOKEN_COUNT] Accurate token count failed, falling back to estimated: {e}")
                return await self.estimated_token_count(system_prompt, messages, tools, thinking_enabled)
        else:
            return await self.estimated_token_count(system_prompt, messages, tools, thinking_enabled)

    async def accurate_token_count(self, system_prompt: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, thinking_enabled: bool = False) -> int:
        """
        Accurate token counting using AWS Bedrock CountTokens API.
        
        Logic:
        1. If thinking_enabled=False: Remove all thinking blocks
        2. If thinking_enabled=True: 
           - Check if last user turn is tool_result
           - If yes, check if the previous assistant turn (with tool_use) has thinking blocks
           - If has thinking blocks → valid, keep thinking enabled
           - If no thinking blocks → invalid, disable thinking
        
        Args:
            thinking_enabled: Whether thinking mode is enabled in the conversation context
        """
        should_enable_thinking = False
        
        if not thinking_enabled:
            # Case 1: thinking_enabled=False → Remove all thinking blocks
            self.logger.debug("[TOKEN_COUNT] thinking_enabled=False, will remove all thinking blocks")
            should_enable_thinking = False
        else:
            # Case 2: thinking_enabled=True → Validate data legality
            last_user_is_tool_result = self._last_user_is_tool_result(messages)
            
            if last_user_is_tool_result:
                # Last user turn is tool_result, check previous assistant turn
                previous_assistant_has_thinking = self._previous_assistant_has_thinking(messages)
                if previous_assistant_has_thinking:
                    # Valid: Previous assistant turn with tool_use has thinking blocks
                    self.logger.debug("[TOKEN_COUNT] Tool continuation with thinking blocks in previous turn, keeping thinking enabled")
                    should_enable_thinking = True
                else:
                    # Invalid: Previous assistant turn with tool_use has no thinking blocks
                    self.logger.warn(
                        "[TOKEN_COUNT] Tool continuation detected but previous assistant turn has no thinking blocks. "
                        "Disabling thinking to avoid ValidationException."
                    )
                    should_enable_thinking = False
            else:
                # Regular user input - safe to enable thinking
                self.logger.debug("[TOKEN_COUNT] Regular user input, keeping thinking enabled")
                should_enable_thinking = True
        
        # Clean messages based on the final decision
        cleaned_messages = self._clean_messages_for_thinking_mode(messages, should_enable_thinking)
        
        if not should_enable_thinking:
            self.logger.debug("[TOKEN_COUNT] Thinking blocks removed from messages to match API call")
        
        input_to_count = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.token_count_config.max_tokens,
            "messages": cleaned_messages,
        }
        if system_prompt:
            input_to_count["system"] = system_prompt
        if tools:
            input_to_count["tools"] = tools
        
        # Enable thinking in API call only if both conditions are met:
        # 1. Thinking is enabled in conversation context
        # 2. Message structure is valid (last assistant starts with thinking)
        if should_enable_thinking:
            self.logger.debug("[TOKEN_COUNT] Enabling thinking mode for CountTokens API")
            input_to_count["thinking"] = {
                "type": "enabled",
                "budget_tokens": 4000  # Default thinking budget tokens
            }
        
        input_to_count = json.dumps(input_to_count)

        retry_count = 0
        while retry_count < self.token_count_config.max_retries:
            try:
                response = self.llm_client.count_tokens(
                    modelId=self.token_count_config.model,
                    input={
                        "invokeModel": {
                            "body": input_to_count
                        }
                    }
                )
                token_count = response['inputTokens']
                return token_count
            except Exception as e:
                import traceback
                # Sanitize base64 content before logging to prevent log bloat
                sanitized_messages = AgentLogger._sanitize_base64_content(messages)
                self.logger.error(f"[TOKEN_COUNT] Could not calculate accurate tokens: {e} \n Messages:\n {json.dumps(sanitized_messages, indent=2, ensure_ascii=False)} \n Traceback:\n {traceback.format_exc()}")
                retry_count += 1
                if retry_count < self.token_count_config.max_retries:
                    self.logger.warn(f"[TOKEN_COUNT] Retrying ({retry_count}/{self.token_count_config.max_retries})...")
                else:
                    self.logger.error(f"[TOKEN_COUNT] Failed to calculate accurate tokens after {self.token_count_config.max_retries} attempts")
                    raise e

    async def estimated_token_count(self, system_prompt: str, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, thinking_enabled: bool = False) -> int:
        # TODO: count_tokens api is not supported in LiteLLM, so we use the following method to count tokens
        # This method is not accurate, but it's the best we can do for now
        token_count = 0
        # if num_previous_input_tokens == 0:
        token_count += await self.count_system_prompt_tokens(system_prompt)
        token_count += await self.count_tool_tokens(tools)
        for message in messages:
            content = message['content']
            # Handle both string and list content formats
            if isinstance(content, str):
                token_count += len(content) / 4
            elif isinstance(content, list):
                for item in content:
                    # Handle nested lists (when content_core itself is a list)
                    if isinstance(item, list):
                        for nested_item in item:
                            if isinstance(nested_item, dict):
                                item_type = nested_item.get('type', '')
                                if item_type == 'text':
                                    token_count += len(nested_item.get('text', '')) / 4
                                elif item_type == 'tool_use':
                                    token_count += len(json.dumps(nested_item.get('input', {}))) / 4
                                elif item_type == 'tool_result':
                                    result_content = nested_item.get('content', '')
                                    if isinstance(result_content, str):
                                        token_count += len(result_content) / 4
                                    elif isinstance(result_content, list):
                                        for rc in result_content:
                                            if isinstance(rc, dict):
                                                token_count += len(rc.get('text', '')) / 4
                            elif isinstance(nested_item, str):
                                token_count += len(nested_item) / 4
                        continue
                    
                    # Handle dict items
                    if not isinstance(item, dict):
                        continue
                    
                    item_type = item.get('type', '')
                    if item_type == 'text':
                        token_count += len(item.get('text', '')) / 4
                    elif item_type == 'tool_use':
                        token_count += len(json.dumps(item.get('input', {}))) / 4
                    elif item_type == 'tool_result':
                        # Handle tool_result with flexible structure
                        if 'content' in item:
                            content_data = item['content']
                            if isinstance(content_data, str):
                                token_count += len(content_data) / 4
                            else:
                                token_count += len(json.dumps(content_data)) / 4
                        else:
                            # Fallback: estimate tokens from entire item except type and tool_use_id
                            fallback_data = {k: v for k, v in item.items() if k not in ['type', 'tool_use_id']}
                            token_count += len(json.dumps(fallback_data)) / 4
                    elif item_type == 'thinking':
                        token_count += len(item.get('thinking', '')) / 4
                        # Add signature tokens if present (signature is not usually counted for user-visible content)
                        if 'signature' in item:
                            token_count += len(item['signature']) / 4
                    elif item_type == 'document':
                        token_count += await self._count_pdf_tokens(item)
                    elif item_type == 'image':
                        token_count += await self._count_image_tokens(item)
                    elif item_type == 'system_reminder':
                        token_count += len(item.get('text', '')) / 4
                    elif item_type == 'compacted_message':
                        token_count += len(item.get('text', '')) / 4
                    else:
                        raise ValueError(f"Unknown content type: {item['type']}")

        return token_count

    async def count_system_prompt_tokens(self, system_prompt: str) -> int:
        return len(system_prompt) / 4

    async def count_tool_tokens(self, tools: List[Dict[str, Any]]) -> int:
        token_count = 0
        if tools:
            for tool in tools:
                token_count += len(json.dumps(tool)) / 4
        return token_count
        
    async def _count_image_tokens(self, content: Dict[str, Any]) -> int:
        """Count tokens for image content using formula: (width * height) / 750"""
        try:
            source = content.get('source', {})
            
            if source.get('type') == 'base64':
                # Handle base64 data
                base64_data = source.get('data')
                if not base64_data:
                    return 0
                    
                # Decode base64 to get image dimensions
                image_data = base64.b64decode(base64_data)
                image = Image.open(io.BytesIO(image_data))
                width, height = image.size
                
            elif source.get('type') == 'url':
                # Handle URL data
                url = source.get('url')
                if not url:
                    return 0
                    
                # Fetch image from URL
                response = httpx.get(url, timeout=30.0)
                response.raise_for_status()
                image_data = response.content
                image = Image.open(io.BytesIO(image_data))
                width, height = image.size
                
            else:
                # Unknown source type, return 0
                return 0
                
            # Calculate tokens using formula: (width * height) / 750
            tokens = int((width * height) / 750)
            return tokens
            
        except Exception as e:
            # If we can't process the image, return a default estimate
            self.logger.error(f"[TOKEN_COUNT] Could not calculate image tokens: {e}")
            return 1000  # Default fallback
    
    async def _count_pdf_tokens(self, content: Dict[str, Any]) -> int:
        """Count tokens for PDF content using formula: pages * 2500 + (tokens when pages viewed as images)"""
        try:
            source = content.get('source', {})
            
            if source.get('type') == 'base64':
                # Handle base64 data
                base64_data = source.get('data')
                if not base64_data:
                    return 0
                    
                # Decode base64 to get PDF data
                pdf_data = base64.b64decode(base64_data)
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
                num_pages = len(pdf_reader.pages)
                
            elif source.get('type') == 'url':
                # Handle URL data
                url = source.get('url')
                if not url:
                    return 0
                    
                # Fetch PDF from URL
                response = httpx.get(url, timeout=30.0)
                response.raise_for_status()
                pdf_data = response.content
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_data))
                num_pages = len(pdf_reader.pages)
                
            else:
                # Unknown source type, return 0
                return 0
            
            # Calculate tokens using formula: pages * 2500 + (tokens when pages viewed as images)
            # Assuming each PDF page as image is approximately 1024x768 pixels
            page_image_tokens = int((1024 * 768) / 750)  # ~1050 tokens per page as image
            total_tokens = num_pages * 2500 + num_pages * page_image_tokens
            return total_tokens
            
        except Exception as e:
            # If we can't process the PDF, return a default estimate
            self.logger.error(f"[TOKEN_COUNT] Could not calculate PDF tokens: {e}")
            return 5000  # Default fallback for a typical PDF
    
    def _clean_messages_for_thinking_mode(self, messages: List[Dict[str, Any]], thinking_enabled: bool) -> List[Dict[str, Any]]:
        """
        Clean messages to be consistent with thinking_enabled parameter.
        
        - If thinking_enabled=False: Remove all thinking/redacted_thinking blocks from messages
        - If thinking_enabled=True: Keep messages as-is
        
        Args:
            messages: Original messages
            thinking_enabled: Whether thinking mode is enabled
            
        Returns:
            Cleaned messages consistent with thinking_enabled parameter
        """
        if thinking_enabled:
            # Thinking enabled - return messages as-is
            return messages
        
        # Thinking disabled - remove all thinking blocks
        cleaned_messages = []
        for message in messages:
            cleaned_message = message.copy()
            content = message.get('content', [])
            
            # Handle string content (no thinking blocks possible)
            if isinstance(content, str):
                cleaned_messages.append(cleaned_message)
                continue
            
            # Handle list content - filter out thinking blocks
            if isinstance(content, list):
                filtered_content = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get('type')
                        # Skip thinking and redacted_thinking blocks
                        if item_type not in ['thinking', 'redacted_thinking']:
                            filtered_content.append(item)
                    else:
                        filtered_content.append(item)
                
                # Only include message if it has content after filtering
                if filtered_content:
                    cleaned_message['content'] = filtered_content
                    cleaned_messages.append(cleaned_message)
                elif message.get('role') == 'user':
                    # Always keep user messages even if empty after filtering
                    cleaned_message['content'] = filtered_content
                    cleaned_messages.append(cleaned_message)
            else:
                # Other content types - keep as-is
                cleaned_messages.append(cleaned_message)
        
        return cleaned_messages
    
    def _last_assistant_has_any_thinking(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if the last assistant message contains any thinking blocks
        
        Returns True if the last assistant message contains thinking or redacted_thinking 
        blocks anywhere in its content (not just at the start).
        
        This is important because: "When thinking is disabled, an `assistant` message in 
        the final position cannot contain `thinking`" - we must enable thinking if blocks exist.
        """
        # Find the last assistant message
        for message in reversed(messages):
            if message.get('role') == 'assistant':
                content = message.get('content', [])
                
                # Check if content contains any thinking blocks
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') in ['thinking', 'redacted_thinking']:
                            return True
                elif isinstance(content, dict):
                    if content.get('type') in ['thinking', 'redacted_thinking']:
                        return True
                
                # Found the last assistant message but no thinking blocks
                return False
        
        # No assistant message found
        return False
    
    def _last_user_is_tool_result(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if the last user message is a tool result
        
        Returns True if the last user message contains a tool_result block.
        This indicates we're in a tool use continuation scenario where the assistant
        is responding after a tool has executed.
        """
        # Find the last user message
        for message in reversed(messages):
            if message.get('role') == 'user':
                content = message.get('content', [])
                
                # Check if content contains a tool_result
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'tool_result':
                            return True
                elif isinstance(content, dict):
                    if content.get('type') == 'tool_result':
                        return True
                
                # Found the last user message but no tool_result
                return False
        
        # No user message found
        return False
    
    def _previous_assistant_has_thinking(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if the previous assistant turn (before last user turn) has thinking blocks
        
        This is used when the last user turn is a tool_result to validate whether the 
        previous assistant turn (which should contain tool_use) has thinking blocks.
        
        Returns True if the assistant message before the last user message contains 
        thinking or redacted_thinking blocks.
        """
        # First, find the last user message index
        last_user_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get('role') == 'user':
                last_user_idx = i
                break
        
        if last_user_idx == -1:
            return False
        
        # Now find the assistant message before the last user message
        for i in range(last_user_idx - 1, -1, -1):
            if messages[i].get('role') == 'assistant':
                content = messages[i].get('content', [])
                
                # Check if content contains any thinking blocks
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') in ['thinking', 'redacted_thinking']:
                            return True
                elif isinstance(content, dict):
                    if content.get('type') in ['thinking', 'redacted_thinking']:
                        return True
                
                # Found the previous assistant message but no thinking blocks
                return False
        
        # No assistant message found before last user message
        return False