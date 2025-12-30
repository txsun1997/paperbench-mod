import httpx
import anthropic

from anthropic import AsyncAnthropicBedrock
from typing import Dict, Any, List, Union, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import *
from utils.exceptions import InvalidToolInputError
from tools.tool_registry import validate_tool_input
from .llm_utils import create_retry_logger
from monitor import AgentLogger


class BedrockClient:
    """AWS Bedrock client for handling Claude API calls with streaming and retries"""
    
    def __init__(self, llm_config: Optional[Union[LLMConfig, CompressionConfig, PhaseConfig]] = None) -> None:
        self.llm_config = llm_config
        
        self.client = AsyncAnthropicBedrock(
            aws_access_key=self.llm_config.aws_access_key.get_secret_value(),
            aws_secret_key=self.llm_config.aws_secret_key.get_secret_value(),
            aws_region=self.llm_config.aws_region
        )
        self.logger = AgentLogger()
    
    def _should_enable_thinking(self, messages: List[Dict[str, Any]], thinking_enabled: bool) -> bool:
        """
        Determine if thinking mode should actually be enabled based on message structure.
        
        When thinking is enabled, Claude's API requires that assistant messages start with
        thinking blocks. After context compaction or when resuming older conversations,
        assistant messages may not have thinking blocks, causing API errors.
        
        Logic:
        1. If thinking_enabled=False: Return False
        2. If thinking_enabled=True:
           - Check if last user turn is tool_result (tool continuation scenario)
           - If yes, check if the previous assistant turn has thinking blocks
           - If no thinking blocks in previous assistant turn, disable thinking to avoid API error
           - Otherwise, enable thinking
        
        Returns:
            Whether thinking should actually be enabled for the API call
        """
        if not thinking_enabled:
            return False
        
        # Check if this is a tool continuation scenario (last user message is tool_result)
        last_user_is_tool_result = self._last_user_is_tool_result(messages)
        
        if last_user_is_tool_result:
            # In tool continuation, we must check if previous assistant has thinking blocks
            previous_assistant_has_thinking = self._previous_assistant_has_thinking(messages)
            if not previous_assistant_has_thinking:
                self.logger.warning(
                    "[BEDROCK] Tool continuation detected but previous assistant turn has no thinking blocks. "
                    "Disabling thinking to avoid ValidationException."
                )
                return False
        
        return True
    
    def _last_user_is_tool_result(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if the last user message contains a tool_result block."""
        for message in reversed(messages):
            if message.get('role') == 'user':
                content = message.get('content', [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'tool_result':
                            return True
                elif isinstance(content, dict):
                    if content.get('type') == 'tool_result':
                        return True
                return False
        return False
    
    def _previous_assistant_has_thinking(self, messages: List[Dict[str, Any]]) -> bool:
        """Check if the assistant message before the last user turn has thinking blocks."""
        # Find the last user message index
        last_user_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get('role') == 'user':
                last_user_idx = i
                break
        
        if last_user_idx == -1:
            return False
        
        # Find the assistant message before the last user message
        for i in range(last_user_idx - 1, -1, -1):
            if messages[i].get('role') == 'assistant':
                content = messages[i].get('content', [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') in ['thinking', 'redacted_thinking']:
                            return True
                elif isinstance(content, dict):
                    if content.get('type') in ['thinking', 'redacted_thinking']:
                        return True
                return False
        
        return False
    
    def _clean_thinking_blocks(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove thinking blocks from all messages when thinking is disabled."""
        cleaned_messages = []
        for message in messages:
            cleaned_message = message.copy()
            content = message.get('content', [])
            
            if isinstance(content, str):
                cleaned_messages.append(cleaned_message)
                continue
            
            if isinstance(content, list):
                filtered_content = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get('type')
                        if item_type not in ['thinking', 'redacted_thinking']:
                            filtered_content.append(item)
                    else:
                        filtered_content.append(item)
                
                if filtered_content:
                    cleaned_message['content'] = filtered_content
                    cleaned_messages.append(cleaned_message)
                elif message.get('role') == 'user':
                    cleaned_message['content'] = filtered_content
                    cleaned_messages.append(cleaned_message)
            else:
                cleaned_messages.append(cleaned_message)
        
        return cleaned_messages
    
    async def call_llm(
        self, 
        system_prompt: Union[str, List[Dict[str, Any]]], 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        thinking_enabled: bool = True,
        cache_control: bool = True,
        business: str = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Call AWS Bedrock Claude API with comprehensive error handling"""
        
        # Validate and adjust thinking mode based on message structure
        # This prevents API errors when assistant messages don't have thinking blocks
        actual_thinking_enabled = self._should_enable_thinking(messages, thinking_enabled)
        if thinking_enabled and not actual_thinking_enabled:
            # Clean thinking blocks from messages since we're disabling thinking
            messages = self._clean_thinking_blocks(messages)
            self.logger.info("[BEDROCK] Thinking disabled due to incompatible message structure")
        
        # Setup cache_control for the last message
        if cache_control:
            last_message = messages[-1]
            if isinstance(last_message['content'], str):
                last_message['content'] = [{"type": "text", "text": last_message['content'], "cache_control": {"type": "ephemeral"}}]
            elif isinstance(last_message['content'], dict):
                last_message['content'] = [last_message['content']]
                last_message['content'][-1]['cache_control'] = {"type": "ephemeral"}
            else:
                last_message['content'][-1]['cache_control'] = {"type": "ephemeral"}
        
        # Build request parameters
        request_params = {
            "model": self.llm_config.model,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            request_params["tools"] = tools
        if self.llm_config.max_tokens:
            request_params["max_tokens"] = self.llm_config.max_tokens
        if self.llm_config.temperature:
            request_params["temperature"] = self.llm_config.temperature
        if self.llm_config.top_p:
            request_params["top_p"] = self.llm_config.top_p
        
        if actual_thinking_enabled:
            request_params["thinking"] = {
                "budget_tokens": self.llm_config.thinking_budget_tokens,
                "type": "enabled"
            }

        request_metadata = {
            key: value
            for key, value in request_params.items()
            if key not in {"messages", "system", "tools"}
        }

        self.logger.llm_request(
            model=self.llm_config.model,
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            parameters=request_metadata,
            provider=self.llm_config.provider,
            vendor=self.llm_config.vendor,
            cache_control=cache_control,
            thinking_enabled=actual_thinking_enabled,
            business=business,
        )

        # Accumulate token usage across all retry attempts
        accumulated_input_tokens = 0
        accumulated_output_tokens = 0
        accumulated_cache_creation_input_tokens = 0
        accumulated_cache_read_input_tokens = 0
        accumulated_ephemeral_5m_input_tokens = 0
        accumulated_ephemeral_1h_input_tokens = 0

        async def _make_request():
            """Internal request handler with streaming support.
            
            Uses SDK's get_final_message() to avoid manually parsing streaming events.
            The SDK handles all the complexity of accumulating content blocks, managing
            indices, and dealing with both raw SSE events and convenience events.
            """
            nonlocal accumulated_input_tokens, accumulated_output_tokens
            nonlocal accumulated_cache_creation_input_tokens, accumulated_cache_read_input_tokens
            nonlocal accumulated_ephemeral_5m_input_tokens, accumulated_ephemeral_1h_input_tokens
            
            async with self.client.messages.stream(**request_params) as stream:
                # Let the SDK handle all streaming event accumulation
                final_message = await stream.get_final_message()
                
                # Extract token usage from the final message
                if hasattr(final_message, 'usage') and final_message.usage:
                    usage = final_message.usage
                    input_tokens = getattr(usage, 'input_tokens', 0)
                    output_tokens = getattr(usage, 'output_tokens', 0)
                    cache_creation_input_tokens = getattr(usage, 'cache_creation_input_tokens', 0)
                    cache_read_input_tokens = getattr(usage, 'cache_read_input_tokens', 0)
                    
                    # Handle cache_creation object if present
                    if hasattr(usage, 'cache_creation') and usage.cache_creation:
                        cache_creation = usage.cache_creation
                        ephemeral_5m_input_tokens = getattr(cache_creation, 'ephemeral_5m_input_tokens', 0)
                        ephemeral_1h_input_tokens = getattr(cache_creation, 'ephemeral_1h_input_tokens', 0)
                    else:
                        ephemeral_5m_input_tokens = 0
                        ephemeral_1h_input_tokens = 0
                else:
                    input_tokens = output_tokens = 0
                    cache_creation_input_tokens = cache_read_input_tokens = 0
                    ephemeral_5m_input_tokens = ephemeral_1h_input_tokens = 0

                # Accumulate token usage from this attempt
                accumulated_input_tokens += input_tokens
                accumulated_output_tokens += output_tokens
                accumulated_cache_creation_input_tokens += cache_creation_input_tokens
                accumulated_cache_read_input_tokens += cache_read_input_tokens
                accumulated_ephemeral_5m_input_tokens += ephemeral_5m_input_tokens
                accumulated_ephemeral_1h_input_tokens += ephemeral_1h_input_tokens
                
                # Build the response in the expected format
                response_content = []
                
                if not final_message.content:
                    raise ValueError(f"Empty response received from LLM: no content blocks. Message: {final_message}")
                
                for block in final_message.content:
                    if block.type == "text":
                        response_content.append({
                            "type": "text",
                            "text": block.text
                        })
                    elif block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input  # SDK already parses the JSON
                        
                        # Validate the tool input
                        validate_tool_input(tool_name, tool_input)

                        response_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": tool_name,
                            "input": tool_input
                        })
                    elif block.type == "thinking":
                        response_content.append({
                            "type": "thinking",
                            "thinking": block.thinking,
                            "signature": getattr(block, 'signature', "")
                        })
                    else:
                        # Log but don't fail on unknown block types for forward compatibility
                        self.logger.warning(f"Unknown content block type: {block.type}")
                
                response_payload = {
                    "role": "assistant",
                    "content": response_content
                }

                return response_payload
        
        # Retry on these exception types:
        # - RateLimitError (429): Rate limiting from AWS Bedrock
        # - APITimeoutError: Request timeout
        # - APIConnectionError: Network connection issues
        # - InternalServerError (500): Temporary server errors
        # - InvalidToolInputError: Tool input validation errors (may be transient)
        # - ValueError: Empty response or unexpected errors
        # - httpx.RemoteProtocolError: Connection closed mid-stream
        retryable_exceptions = (
            anthropic.RateLimitError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError,
            InvalidToolInputError,
            ValueError,
            httpx.RemoteProtocolError,
        )
        
        response_message = await retry(
            stop=stop_after_attempt(self.llm_config.num_retries),
            wait=wait_exponential(multiplier=self.llm_config.retry_multiplier, min=self.llm_config.retry_start_wait),
            retry=retry_if_exception_type(retryable_exceptions),
            before_sleep=create_retry_logger(self.logger),
            reraise=True,
        )(_make_request)()

        # Build usage payload with accumulated tokens from all attempts
        response_usage = {
            "usage_from_model": {
                "name": self.llm_config.model,
                "vendor": self.llm_config.vendor,
                "provider": self.llm_config.provider
            },
            "input_tokens": accumulated_input_tokens,
            "output_tokens": accumulated_output_tokens,
            "cache_creation_input_tokens": accumulated_cache_creation_input_tokens,
            "cache_read_input_tokens": accumulated_cache_read_input_tokens,
            "ephemeral_5m_input_tokens": accumulated_ephemeral_5m_input_tokens,
            "ephemeral_1h_input_tokens": accumulated_ephemeral_1h_input_tokens,
        }

        # Pop out cache_control from response
        if cache_control:
            last_message['content'][-1].pop("cache_control", None)

        self.logger.llm_response(
            model=self.llm_config.model,
            response=response_message,
            usage=response_usage,
            provider=self.llm_config.provider,
            vendor=self.llm_config.vendor,
            business=business,
        )

        return response_message, response_usage

