import json
import asyncio
from abc import ABC, abstractmethod
import re
from typing import Dict, Any, List, Optional, Tuple
import uuid

from config import AgentsConfig
from memory import MemoryManager
from llm.token_counter import TokenCounter
from llm.client_factory import create_llm_client
from monitor.logger import AgentLogger
from message import Message, LocalMessageStore
from tools.tool_registry import get_all_claude_tools
from tools.local_tool_executor import LocalToolExecutor


class BaseAgent(ABC):
    """
    Base class for all agents - refactored for stateful local operation.
    
    Key changes from original:
    - Uses LocalMessageStore instead of RemoteMessageService
    - Maintains conversation state across turns
    - Simplified to remove backend communication
    """
    
    def __init__(
        self, 
        agents_config: AgentsConfig, 
        working_dir: str,
        task_id: str = None
    ):
        self.agents_config = agents_config
        self.task_id = task_id if task_id else str(uuid.uuid4())
        self.working_dir = working_dir
        
        # Initialize logger
        self.logger = AgentLogger(task_id=self.task_id)
        
        # Initialize LLM client
        self.llm_client = create_llm_client(self.agents_config.llm)
        
        # Initialize local message store (replaces RemoteMessageService)
        self.message_store = LocalMessageStore()
        
        # Initialize tool executor
        self.tool_executor = LocalToolExecutor(working_dir=working_dir, task_id=self.task_id)
        
        # Initialize tools
        self.tools = get_all_claude_tools()
        
        # System prompt will be set by subclass
        self._system_prompt: Optional[str] = None
        
        # Initialize token counter
        self.token_counter = TokenCounter(token_count_config=self.agents_config.token_count)
        
        # Initialize memory manager
        self.memory_manager = MemoryManager(
            token_counter=self.token_counter,
            compression_config=self.agents_config.compression
        )
        self.memory_manager.update_tools(self.tools)
        
        # Bind task_id to components
        self._bind_task_id_to_components(self.task_id)
    
    def _bind_task_id_to_components(self, task_id: str) -> None:
        """Propagate task_id to all sub-components that maintain their own loggers."""
        components = [
            self.llm_client,
            self.token_counter,
            self.memory_manager,
            getattr(self.memory_manager, "llm_client", None),
        ]
        
        for component in components:
            self._assign_task_id(component, task_id)
    
    @staticmethod
    def _assign_task_id(component: Any, task_id: str) -> None:
        if not component:
            return
        
        component_logger = getattr(component, "logger", None)
        if isinstance(component_logger, AgentLogger):
            component_logger.set_task_id(task_id)
    
    def get_system_prompt(self) -> str:
        if not self._system_prompt:
            raise RuntimeError("System prompt not initialized. Subclass must set _system_prompt.")
        return self._system_prompt
    
    def add_user_message(self, content: str) -> None:
        """Add a user text message to the conversation"""
        message = Message(
            role="user",
            type="text",
            content_core={"type": "text", "text": content}
        )
        self.message_store.add_message(message)
        self.logger.info(f"Added user message: {content[:100]}...")
    
    def add_user_message_dict(self, message_dict: Dict[str, Any]) -> None:
        """Add a user message from dictionary (for tool results, etc.)"""
        message = Message.from_dict(message_dict)
        self.message_store.add_message(message)
    
    def _is_empty_llm_response(self, llm_response_dict: Dict[str, Any]) -> bool:
        """Check if LLM response is empty (no meaningful content)"""
        content = llm_response_dict.get("content", [])
        
        if not content:
            return True
        
        has_meaningful_content = False
        for block in content:
            block_type = block.get("type")
            if block_type == "tool_use":
                has_meaningful_content = True
                break
            elif block_type == "text":
                text = block.get("text", "").strip()
                if text:
                    has_meaningful_content = True
                    break
            elif block_type == "thinking":
                # Thinking blocks don't count as meaningful output on their own
                continue
        
        return not has_meaningful_content
    
    def _get_user_friendly_error_message(self, exception: Exception) -> str:
        """Convert exception to user-friendly error message."""
        import anthropic
        
        exception_type = type(exception).__name__
        exception_str = str(exception).lower()
        
        # Check for timeout errors
        if isinstance(exception, anthropic.APITimeoutError):
            return "Request timeout, please try again later"
        
        # Check for rate limit errors
        if isinstance(exception, anthropic.RateLimitError):
            return "Rate limit exceeded, please try again later"
        
        # Check for timeout keywords in error message
        if any(keyword in exception_str for keyword in ['timeout', 'timed out', 'time out']):
            return "Request timeout, please try again later"
        
        # Check for rate limit keywords in error message
        if any(keyword in exception_str for keyword in ['rate limit', 'rate_limit', 'quota', 'too many requests', 'too many tokens']):
            return "Rate limit exceeded, please try again later"
        
        # All other errors are treated as internal errors
        return f"Internal error: {str(exception)}"
    
    async def _convert_messages_to_llm_format(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert Message objects to LLM-compatible format"""
        llm_messages = []
        current_role = None
        current_content = []
        
        for msg in messages:
            # If role changes, save the accumulated message
            if current_role and msg.role != current_role:
                llm_messages.append({
                    "role": current_role,
                    "content": current_content
                })
                current_content = []
            
            current_role = msg.role
            # If content_core is already a list, extend; otherwise append
            if isinstance(msg.content_core, list):
                current_content.extend(msg.content_core)
            else:
                current_content.append(msg.content_core)
        
        # Add the last accumulated message
        if current_role:
            llm_messages.append({
                "role": current_role,
                "content": current_content
            })
        
        return llm_messages
    
    @abstractmethod
    def _initialize_system_prompt(self) -> None:
        """Initialize agent-specific system prompt. Must be implemented by subclass."""
        pass
    
    async def run_turn(self) -> Dict[str, Any]:
        """
        Execute one conversation turn.
        
        Returns:
            Dict with agent response, including:
            - success: bool
            - response: dict with role and content
            - message: error message if failed
        """
        in_context_messages = self.message_store.get_messages()
        current_plan = self.message_store.get_plan()
        current_todos = self.message_store.get_todos()
        
        thinking_enabled = True
        
        self.logger.debug(f"[RUN_TURN] Processing {len(in_context_messages)} messages")
        
        if not in_context_messages:
            self.logger.error("[RUN_TURN] No messages to process")
            return {
                "success": False,
                "response": None,
                "message": "No messages in conversation"
            }
        
        # Check if compression is needed
        llm_compatible_messages = await self._convert_messages_to_llm_format(in_context_messages)
        
        if await self.memory_manager.should_compress(
            messages=llm_compatible_messages,
            system_prompt=self.get_system_prompt(),
            max_tokens=self.agents_config.llm.max_context_tokens,
            thinking_enabled=thinking_enabled
        ):
            self.logger.info("[RUN_TURN] Context compression needed")
            await self._execute_compression(in_context_messages, current_plan, current_todos)
            # Refresh messages after compression
            in_context_messages = self.message_store.get_messages()
            llm_compatible_messages = await self._convert_messages_to_llm_format(in_context_messages)
        
        # Call LLM
        total_token_usage = []
        max_llm_attempts = 2
        
        for attempt in range(max_llm_attempts):
            try:
                llm_response_dict, agent_response_token_usage = await self.llm_client.call_llm(
                    system_prompt=self.get_system_prompt(),
                    messages=llm_compatible_messages,
                    tools=self.tools,
                    thinking_enabled=thinking_enabled,
                    business="agent_service"
                )
                total_token_usage.append({
                    "token_usage": agent_response_token_usage,
                    "business": "agent_response"
                })
                
                # Check if response is empty
                if not self._is_empty_llm_response(llm_response_dict):
                    # Add assistant response to message store
                    assistant_message = Message(
                        role="assistant",
                        type="tool_use" if any(b.get("type") == "tool_use" for b in llm_response_dict["content"]) else "text",
                        content_core=llm_response_dict["content"],
                        token_usage=agent_response_token_usage
                    )
                    self.message_store.add_message(assistant_message)
                    
                    return {
                        "success": True,
                        "response": llm_response_dict,
                        "token_usage": total_token_usage
                    }
                
                # Empty response received
                self.logger.error(f"[LLM_ERROR] Empty response (attempt {attempt + 1}/{max_llm_attempts})")
                
                if attempt == (max_llm_attempts - 1):
                    return {
                        "success": False,
                        "response": None,
                        "message": "Internal service error, please try again later",
                        "token_usage": total_token_usage
                    }
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                error_msg = str(e).replace('{', '{{').replace('}', '}}')
                self.logger.error(f"[LLM_ERROR] Error during LLM call (attempt {attempt + 1}/{max_llm_attempts}): {error_msg}", exc_info=True)
                
                if attempt == (max_llm_attempts - 1):
                    user_message = self._get_user_friendly_error_message(e)
                    return {
                        "success": False,
                        "response": None,
                        "message": user_message,
                        "token_usage": total_token_usage
                    }
        
        return {
            "success": False,
            "response": None,
            "message": "Maximum retry attempts exceeded"
        }
    
    async def execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute tool calls from LLM response and add results to message store.
        
        Args:
            tool_calls: List of tool use blocks from LLM response
            
        Returns:
            List of tool result dictionaries
        """
        tool_results = []
        
        for tool_call in tool_calls:
            if tool_call.get("type") != "tool_use":
                continue
            
            tool_name = tool_call.get("name")
            tool_input = tool_call.get("input", {})
            tool_use_id = tool_call.get("id")
            
            self.logger.info(f"[TOOL_EXEC] Executing {tool_name}")
            
            # Execute tool
            result = await self.tool_executor.execute_tool(tool_name, tool_input)
            
            # Create tool result message
            tool_result_msg = Message(
                role="user",
                type="tool_result",
                content_core={
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result.get("result", "")
                }
            )
            self.message_store.add_message(tool_result_msg)
            
            tool_results.append({
                "tool_name": tool_name,
                "success": result.get("success", False),
                "result": result.get("result", "")
            })
        
        return tool_results
    
    async def _execute_compression(
        self,
        in_context_messages: List[Message],
        current_plan: str,
        current_todos: List[Dict[str, Any]]
    ) -> None:
        """Execute context compression and update message store"""
        try:
            result = await self.memory_manager.compact_context_messages(
                in_context_messages=in_context_messages
            )
            
            if result and result.get("compacted_message"):
                # Create a compacted message
                compacted_msg = Message(
                    role="user",
                    type="compacted_message",
                    content_core=result["compacted_message"]["content"]
                )
                
                # Clear old messages and add compacted message
                # Keep recent messages based on compression result
                self.message_store.messages = [compacted_msg] + in_context_messages[len(in_context_messages) - result.get("kept_count", 10):]
                
                self.logger.info("[COMPRESSION] Successfully compressed context")
            else:
                self.logger.warning("[COMPRESSION] Compression failed or not needed")
        
        except Exception as e:
            self.logger.error(f"[COMPRESSION] Error during compression: {e}", exc_info=True)
    
    async def cleanup(self):
        """Cleanup agent resources"""
        if self.tool_executor:
            await self.tool_executor.cleanup()
