import json
from openai import AsyncOpenAI
from typing import Dict, Any, List, Union, Optional, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai
import httpx

from config import *
from utils.exceptions import InvalidToolJSONError, InvalidToolInputError
from tools.tool_registry import validate_tool_input
from .llm_utils import create_retry_logger
from monitor import AgentLogger


class OpenRouterClient:
    """OpenAI client for handling Claude API calls through OpenRouter with streaming and retries"""
    
    def __init__(self, llm_config: Optional[Union[LLMConfig, CompressionConfig]] = None) -> None:
        self.llm_config = llm_config
        self.client = AsyncOpenAI(
            api_key=self.llm_config.openrouter_api_key.get_secret_value(),
            base_url=self.llm_config.openrouter_base_url
        )
        self.logger = AgentLogger()
    
    def _convert_system_prompt_to_openai(self, system_prompt: Union[str, List[Dict[str, Any]]]) -> str:
        """Convert Anthropic system prompt format to OpenAI format"""
        if isinstance(system_prompt, str):
            return system_prompt
        
        # If it's a list of content blocks, extract text
        text_parts = []
        for block in system_prompt:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        
        return "\n\n".join(text_parts)
    
    def _convert_messages_to_openai(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Anthropic message format to OpenAI format"""
        openai_messages = []
        
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            
            # Handle different content formats
            if isinstance(content, str):
                openai_messages.append({
                    "role": role,
                    "content": content
                })
            elif isinstance(content, list):
                # First, check if this user message contains tool_results
                # In OpenAI format, tool_results need separate role="tool" messages
                tool_results = [block for block in content if block.get("type") == "tool_result"]
                non_tool_blocks = [block for block in content if block.get("type") != "tool_result"]
                
                # Handle tool_results as separate messages with role="tool"
                for tool_result in tool_results:
                    openai_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_result.get("tool_use_id"),
                        "content": tool_result.get("content", "")
                    })
                
                # Convert remaining content blocks
                openai_content = []
                for block in non_tool_blocks:
                    block_type = block.get("type")
                    
                    if block_type == "text":
                        openai_content.append({
                            "type": "text",
                            "text": block.get("text", "")
                        })
                    elif block_type == "image":
                        # Convert Anthropic image format to OpenAI format
                        source = block.get("source", {})
                        if source.get("type") == "base64":
                            media_type = source.get("media_type", "image/jpeg")
                            data = source.get("data", "")
                            openai_content.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{data}"
                                }
                            })
                    elif block_type == "tool_use":
                        # For assistant messages with tool calls
                        pass  # Handle separately
                    elif block_type == "thinking":
                        # OpenAI doesn't support thinking blocks, skip them
                        pass
                
                # Handle tool_calls separately for assistant messages
                tool_calls = []
                for block in content:
                    if block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block.get("id"),
                            "type": "function",
                            "function": {
                                "name": block.get("name"),
                                "arguments": json.dumps(block.get("input", {}))
                            }
                        })
                
                # Add message if has content or tool_calls (but skip if we only had tool_results)
                if openai_content or (tool_calls and role == "assistant"):
                    # If only one text block, simplify to string
                    if openai_content and len(openai_content) == 1 and openai_content[0].get("type") == "text":
                        content_value = openai_content[0].get("text", "")
                    elif openai_content:
                        content_value = openai_content
                    else:
                        # For assistant with only tool_calls, use empty string
                        content_value = ""
                    
                    msg_dict = {
                        "role": role,
                        "content": content_value
                    }
                    
                    if tool_calls and role == "assistant":
                        msg_dict["tool_calls"] = tool_calls
                    
                    openai_messages.append(msg_dict)
        
        return openai_messages
    
    def _convert_tools_to_openai(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """Convert Anthropic tools format to OpenAI format"""
        if not tools:
            return None
        
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                    "parameters": tool.get("input_schema", {})
                }
            })
        
        return openai_tools
    
    async def call_llm(
        self, 
        system_prompt: Union[str, List[Dict[str, Any]]], 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        thinking_enabled: bool = True,
        cache_control: bool = True,
        business: str = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Call OpenAI API (OpenRouter) with comprehensive error handling
        
        This method maintains the same interface as AnthropicClient.call_llm()
        but uses OpenAI-compatible API format.
        """
        
        # Note: OpenAI doesn't support cache_control, ignore it
        # Note: OpenAI doesn't support thinking blocks natively
        
        # # Handle thinking blocks based on mode
        # if not thinking_enabled and thinking_mode_handler:
        #     # Clean thinking blocks when thinking is disabled
        #     messages = thinking_mode_handler.clean_thinking_from_messages(messages)
        
        # Convert formats
        openai_system = self._convert_system_prompt_to_openai(system_prompt)
        openai_messages = self._convert_messages_to_openai(messages)
        openai_tools = self._convert_tools_to_openai(tools)
        
        # Add system prompt as first message
        if openai_system:
            openai_messages.insert(0, {
                "role": "system",
                "content": openai_system
            })
        
        # Build request parameters
        request_params = {
            "model": self.llm_config.openrouter_model,
            "messages": openai_messages,
            "stream": True,
        }
        
        if openai_tools:
            request_params["tools"] = openai_tools
        if self.llm_config.max_tokens:
            request_params["max_tokens"] = self.llm_config.max_tokens
        if self.llm_config.temperature:
            request_params["temperature"] = self.llm_config.temperature
        if self.llm_config.top_p:
            request_params["top_p"] = self.llm_config.top_p

        request_metadata = {
            key: value
            for key, value in request_params.items()
            if key not in {"messages", "tools"}
        }

        self.logger.llm_request(
            model=self.llm_config.openrouter_model,
            system_prompt=openai_system,
            messages=openai_messages,
            tools=openai_tools,
            parameters=request_metadata,
            provider=self.llm_config.provider,
            vendor=self.llm_config.vendor,
            cache_control=cache_control,
            thinking_enabled=thinking_enabled,
            business=business,
        )

        # Accumulate token usage across all retry attempts
        accumulated_input_tokens = 0
        accumulated_output_tokens = 0

        async def _make_request():
            """Internal request handler with streaming support"""
            nonlocal accumulated_input_tokens, accumulated_output_tokens
            
            stream = await self.client.chat.completions.create(**request_params)
            
            content_blocks = []
            tool_calls_dict = {}  # Track tool calls by index
            current_text = ""
            input_tokens = 0
            output_tokens = 0
            
            async for chunk in stream:
                # Extract usage information
                if hasattr(chunk, 'usage') and chunk.usage:
                    input_tokens = getattr(chunk.usage, 'prompt_tokens', 0)
                    output_tokens = getattr(chunk.usage, 'completion_tokens', 0)
                
                if not chunk.choices:
                    continue
                
                choice = chunk.choices[0]
                delta = choice.delta
                
                # Handle text content
                if hasattr(delta, 'content') and delta.content:
                    current_text += delta.content
                
                # Handle tool calls
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        index = tool_call_delta.index
                        
                        if index not in tool_calls_dict:
                            tool_calls_dict[index] = {
                                "id": tool_call_delta.id or "",
                                "name": "",
                                "arguments": ""
                            }
                        
                        if tool_call_delta.id:
                            tool_calls_dict[index]["id"] = tool_call_delta.id
                        
                        if hasattr(tool_call_delta, 'function'):
                            if tool_call_delta.function.name:
                                tool_calls_dict[index]["name"] = tool_call_delta.function.name
                            if tool_call_delta.function.arguments:
                                tool_calls_dict[index]["arguments"] += tool_call_delta.function.arguments
            
            # Accumulate token usage from this attempt (even if it fails later)
            accumulated_input_tokens += input_tokens
            accumulated_output_tokens += output_tokens
            
            # Build response in Anthropic format
            response_content = []
            
            # Add text content if present
            if current_text:
                response_content.append({
                    "type": "text",
                    "text": current_text
                })
            
            # Add tool calls in Anthropic format
            for tool_call in tool_calls_dict.values():
                try:
                    parsed_arguments = json.loads(tool_call["arguments"]) if tool_call["arguments"] else {}
                except (json.JSONDecodeError, TypeError) as e:
                    # This is a genuine JSON error
                    raise InvalidToolJSONError(f"Invalid tool_use JSON emitted by LLM: {tool_call}")
                
                tool_name = tool_call["name"]
                tool_input = parsed_arguments
                # Validate the tool input, raise InvalidToolInputError if validation fails
                validate_tool_input(tool_name, tool_input)
                
                response_content.append({
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_name,
                    "input": tool_input
                })
            
            # Check if response is completely empty (no content received)
            if not response_content:
                raise ValueError(f"Empty response received from LLM: no content in streaming response. Output tokens: {output_tokens}")
            
            response_payload = {
                "role": "assistant",
                "content": response_content
            }

            return response_payload
        
        response_message = await retry(
            stop=stop_after_attempt(self.llm_config.num_retries),
            wait=wait_exponential(multiplier=self.llm_config.retry_multiplier, min=self.llm_config.retry_start_wait),
            retry=retry_if_exception_type((
                openai.RateLimitError, 
                openai.APITimeoutError, 
                InvalidToolJSONError, 
                InvalidToolInputError,
                httpx.RemoteProtocolError,  # Network connection errors
                httpx.ReadTimeout,  # Read timeout errors
            )),
            before_sleep=create_retry_logger(self.logger),
            reraise=True,
        )(_make_request)()

        # Build usage payload with accumulated tokens from all attempts
        response_usage = {
            "usage_from_model": {
                "name": self.llm_config.openrouter_model,
                "vendor": self.llm_config.vendor,
                "provider": self.llm_config.provider
            },
            "business": "agent_response",
            "input_tokens": accumulated_input_tokens,
            "output_tokens": accumulated_output_tokens,
        }

        self.logger.llm_response(
            model=self.llm_config.openrouter_model,
            response=response_message,
            usage=response_usage,
            provider=self.llm_config.provider,
            vendor=self.llm_config.vendor,
            business=business,
        )

        return response_message, response_usage

