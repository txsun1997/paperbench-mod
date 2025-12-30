import json
import anthropic
import httpx
from typing import Dict, Any, List, Union, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config import *
from utils.exceptions import InvalidToolJSONError, InvalidToolInputError
from tools.tool_registry import validate_tool_input
from .llm_utils import create_retry_logger
from monitor import AgentLogger


class AnthropicClient:
    """Anthropic client for handling Claude API calls with streaming and retries"""
    
    def __init__(self, llm_config: Optional[Union[LLMConfig, CompressionConfig]] = None) -> None:
        self.llm_config = llm_config
        self.client = anthropic.AsyncAnthropic(
            api_key=self.llm_config.api_key.get_secret_value(),
            base_url=self.llm_config.base_url if self.llm_config.base_url else None
        )
        self.logger = AgentLogger()
    
    def _should_enable_thinking(self, messages: List[Dict[str, Any]], thinking_enabled: bool) -> bool:
        """
        Determine if thinking mode should actually be enabled based on message structure.
        
        When thinking is enabled, Claude's API requires that assistant messages start with
        thinking blocks. After context compaction or when resuming older conversations,
        assistant messages may not have thinking blocks, causing API errors.
        """
        if not thinking_enabled:
            return False
        
        last_user_is_tool_result = self._last_user_is_tool_result(messages)
        
        if last_user_is_tool_result:
            previous_assistant_has_thinking = self._previous_assistant_has_thinking(messages)
            if not previous_assistant_has_thinking:
                self.logger.warning(
                    "[ANTHROPIC] Tool continuation detected but previous assistant turn has no thinking blocks. "
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
        last_user_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get('role') == 'user':
                last_user_idx = i
                break
        
        if last_user_idx == -1:
            return False
        
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
        """Call Claude API with comprehensive error handling"""
        
        # Validate and adjust thinking mode based on message structure
        actual_thinking_enabled = self._should_enable_thinking(messages, thinking_enabled)
        if thinking_enabled and not actual_thinking_enabled:
            messages = self._clean_thinking_blocks(messages)
            self.logger.info("[ANTHROPIC] Thinking disabled due to incompatible message structure")
        
        # Disable cache_control for third-party proxies (only supported by official Anthropic API)
        # Third-party proxies like yourouter, openrouter don't support prompt caching
        if self.llm_config.provider in ["yourouter", "openrouter"]:
            if cache_control:
                self.logger.debug(
                    f"Disabling cache_control for provider '{self.llm_config.provider}' "
                    "(prompt caching only supported by official Anthropic API and AWS Bedrock)"
                )
            cache_control = False
        
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
            """Internal request handler with streaming support"""
            nonlocal accumulated_input_tokens, accumulated_output_tokens
            nonlocal accumulated_cache_creation_input_tokens, accumulated_cache_read_input_tokens
            nonlocal accumulated_ephemeral_5m_input_tokens, accumulated_ephemeral_1h_input_tokens
            
            async with self.client.messages.stream(**request_params) as stream:
                content_blocks = []
                input_tokens = 0
                output_tokens = 0
                cache_creation_input_tokens = 0
                cache_read_input_tokens = 0
                ephemeral_5m_input_tokens = 0
                ephemeral_1h_input_tokens = 0
                
                async for chunk in stream:
                    if chunk.type == "message_start":
                        # Capture input tokens from message_start
                        if hasattr(chunk, 'message') and hasattr(chunk.message, 'usage'):
                            usage = chunk.message.usage
                            input_tokens += getattr(usage, 'input_tokens', 0)
                            output_tokens += getattr(usage, 'output_tokens', 0)
                            cache_creation_input_tokens += getattr(usage, 'cache_creation_input_tokens', 0)
                            cache_read_input_tokens += getattr(usage, 'cache_read_input_tokens', 0)
                            # Handle cache_creation object if present
                            if hasattr(usage, 'cache_creation') and usage.cache_creation:
                                cache_creation = usage.cache_creation
                                ephemeral_5m_input_tokens += getattr(cache_creation, 'ephemeral_5m_input_tokens', 0)
                                ephemeral_1h_input_tokens += getattr(cache_creation, 'ephemeral_1h_input_tokens', 0)
                    elif chunk.type == "content_block_start":
                        if chunk.content_block.type == "text":
                            content_blocks.append({
                                "type": "text",
                                "text": ""
                            })
                        elif chunk.content_block.type == "tool_use":
                            content_blocks.append({
                                "type": "tool_use",
                                "id": chunk.content_block.id,
                                "name": chunk.content_block.name,
                                "input": ""
                            })
                        elif chunk.content_block.type == "thinking":
                            content_blocks.append({
                                "type": "thinking",
                                "thinking": "",
                                "signature": ""
                            })
                        else:
                            raise ValueError(f"Unknown content block type: {chunk.content_block.type}")
                    elif chunk.type == "content_block_delta":
                        if chunk.delta.type == "text_delta":
                            content_blocks[-1]["text"] += chunk.delta.text
                        elif chunk.delta.type == "input_json_delta":
                            # Accumulate JSON string, don't try to parse partial JSON
                            content_blocks[-1]["input"] += chunk.delta.partial_json or ""
                        elif chunk.delta.type == "thinking_delta":
                            content_blocks[-1]["thinking"] += chunk.delta.thinking
                        elif chunk.delta.type == "signature_delta":
                            # Handle signature delta for thinking blocks
                            content_blocks[-1]["signature"] += getattr(chunk.delta, 'signature', '')
                        else:
                            raise ValueError(f"Unknown content block delta type: {chunk.delta.type}")
                    elif chunk.type == "message_delta":
                        # Capture output tokens from message_delta
                        if hasattr(chunk, 'usage'):
                            output_tokens += getattr(chunk.usage, 'output_tokens', 0)

                # Accumulate token usage from this attempt (even if it fails later)
                accumulated_input_tokens += input_tokens
                accumulated_output_tokens += output_tokens
                accumulated_cache_creation_input_tokens += cache_creation_input_tokens
                accumulated_cache_read_input_tokens += cache_read_input_tokens
                accumulated_ephemeral_5m_input_tokens += ephemeral_5m_input_tokens
                accumulated_ephemeral_1h_input_tokens += ephemeral_1h_input_tokens
                
                # Build the response in the expected format
                response_content = []
                for block in content_blocks:
                    if block["type"] == "text":
                        response_content.append({
                            "type": "text",
                            "text": block["text"]
                        })
                    elif block["type"] == "tool_use":
                        # Parse the accumulated JSON string
                        try:
                            parsed_input = json.loads(block["input"]) if block["input"] else {}
                        except (json.JSONDecodeError, TypeError) as e:
                            # This is a genuine JSON error; raise a specific error to trigger retry
                            raise InvalidToolJSONError(f"Invalid tool_use JSON emitted by LLM: {block}")
                        
                        tool_name = block["name"]
                        tool_input = parsed_input
                        # Validate the tool input, raise InvalidToolInputError if validation fails
                        validate_tool_input(tool_name, tool_input)
                        
                        response_content.append({
                            "type": "tool_use",
                            "id": block["id"],
                            "name": tool_name,
                            "input": tool_input
                        })
                    elif block["type"] == "thinking":
                        response_content.append({
                            "type": "thinking",
                            "thinking": block["thinking"],
                            "signature": block.get("signature", "")
                        })
                    else:
                        raise ValueError(f"Unknown content block type: {block['type']}. Should not happen")
                
                # Check if response is completely empty (no content blocks received)
                if not response_content:
                    raise ValueError(f"Empty response received from LLM: no content blocks in streaming response. Output tokens: {output_tokens}")
                
                response_payload = {
                    "role": "assistant",
                    "content": response_content
                }

                return response_payload
        
        # Retry on these exception types:
        # - RateLimitError (429): Rate limiting
        # - APITimeoutError: Request timeout
        # - APIConnectionError: Network connection issues
        # - InternalServerError (500): Temporary server errors
        # - BadRequestError: Some bad requests may be transient
        # - InvalidToolJSONError: Tool JSON parsing errors (may be transient)
        # - InvalidToolInputError: Tool input validation errors (may be transient)
        # - ValueError: JSON parsing errors in streaming (SDK internal errors)
        retryable_exceptions = (
            anthropic.RateLimitError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
            anthropic.InternalServerError,
            InvalidToolJSONError,
            InvalidToolInputError,
            httpx.RemoteProtocolError,  # Network connection errors
            httpx.ReadTimeout,  # Read timeout errors
            ValueError,  # JSON parsing errors in SDK streaming
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
