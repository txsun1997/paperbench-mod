import time
import asyncio
import re
import anthropic
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

from config import CompressionConfig
from llm.client_factory import create_llm_client
from utils import load_prompt_template
from monitor import AgentLogger
from message import Message
from message.message_store import LocalMessageStore


class MemoryManager:
    """Memory management functionality for agent conversations including intelligent compression
    
    This class is responsible for:
    - Context compression using LLM-based intelligent analysis
    - Token counting and context size management
    - Tool context management for compression
    """
    
    def __init__(self, token_counter=None, compression_config: Optional[CompressionConfig] = None):
        self.token_counter = token_counter
        self.compression_config = compression_config
        self.tools = None  # Tools list for token counting
        
        # Initialize logger for compression tracing
        self.logger = AgentLogger()
        
        # Initialize LLM client for compression if LLM config is provided
        self.llm_client = create_llm_client(compression_config)

        # Load prompt templates once during initialization
        self.sys_reminder_compact = load_prompt_template('user_sys_reminder_compact.md')
        self.sys_compact_message_bridge = load_prompt_template('compact_message_bridge.md')
        
        # Load prompt templates for LLM-based compression
        self.sys_identity = load_prompt_template('sys_identity.md')
        self.sys_compact = load_prompt_template('sys_compact.md')
        self.user_compact = load_prompt_template('user_compact.md')
        
        # Validate that all required prompt templates are loaded successfully
        self._validate_prompt_templates()


    def _validate_prompt_templates(self):
        """
        Validate that all required prompt templates are loaded successfully.
        Raises RuntimeError if any template is None or empty.
        """
        required_templates = {
            'sys_reminder_compact': self.sys_reminder_compact,
            'sys_compact_message_bridge': self.sys_compact_message_bridge,
            'sys_identity': self.sys_identity,
            'sys_compact': self.sys_compact,
            'user_compact': self.user_compact
        }
        
        empty_templates = []
        
        for template_name, template_content in required_templates.items():
            if not template_content or not template_content.strip():
                empty_templates.append(template_name)
        
        if empty_templates:
            error_msg = "[MEMORY_MANAGER_INIT] Failed to load required prompt templates:"
            
            error_msg += f"\n  Empty templates: {', '.join(empty_templates)}"
            self.logger.error(f"[MEMORY_MANAGER_INIT] Empty templates: {empty_templates}")
            
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        self.logger.info("[MEMORY_MANAGER_INIT] All prompt templates loaded successfully")


    def build_context_messages_after_compact(self, messages_to_compress: List[Message], compacted_string: str) -> str:
        user_messages = [msg for msg in messages_to_compress if msg.role == "user"]
        selected_messages = []
        threshold = 20000 # max 2w tokens for user messages, estimated
        current_tokens = 0
        
        # Traverse from newest to oldest (from the end)
        for msg in reversed(user_messages):
            if msg.type == 'tool_result':
                # skip tool result
                continue

            # Filter out prev compacted result
            if msg.type == 'compacted_message':
                match = re.search(
                    r'<user_message>.*</user_message>', 
                    msg.content_core.get('text', ''), 
                    re.DOTALL)
                if match:
                    text = match.group(0)
                    text = text.replace("<user_message>", '').replace('</user_message>', '').strip()

                    if "User:" not in text:
                        # (No user messages) for this compacted_message
                        continue
                    estimated_tokens = len(text) // 4
                    
                    # Check if adding this text would exceed threshold
                    if current_tokens + estimated_tokens <= threshold:
                        selected_messages.insert(0, ('compacted', text))
                        current_tokens += estimated_tokens
                    else:
                        break
                continue    # skip for compacted_message
                
            # Extract content_core, which is a dict
            content_core = msg.content_core
            
            if isinstance(content_core, dict):
                content_type = content_core.get("type")
                # Only process if it's text type (skip system_reminder)
                if content_type == "text":
                    text = content_core.get("text", "").strip()
                    if text:
                        # Remove system-reminder tags and their content
                        text = re.sub(r'<system-reminder>.*?</system-reminder>', '', text, flags=re.DOTALL)
                        text = text.strip('"\'').strip()
                        
                        if text:  # Only process if there's remaining text after removing system-reminder
                            # Estimate tokens
                            estimated_tokens = len(text) // 4
                            
                            # Check if adding this text would exceed threshold
                            if current_tokens + estimated_tokens <= threshold:
                                selected_messages.insert(0, ('normal', text))  # Insert at beginning to maintain order
                                current_tokens += estimated_tokens
                            else:
                                break
            
            # If we've reached the threshold, stop processing
            if current_tokens >= threshold:
                break
        
        # Concatenate selected_messages and compacted_string to create final message
        user_context = ""
        for msg_type, msg in selected_messages:
            if msg_type == 'normal':
                user_context += f"User: {msg}\n\n"
            elif msg_type == 'compacted':
                user_context += f"{msg.strip()}\n\n"
        user_context = user_context.strip()
        if not user_context:
            user_context = "(No user messages)"
        final_message = self.sys_compact_message_bridge.format(summary=compacted_string, user_message=user_context).strip()
        self.logger.info(f"[BUILD_CONTEXT_MESSAGES_AFTER_COMPACT] summary: {len(compacted_string)} chars, user_context: {len(user_context)} chars, {len(selected_messages)} messages, final_message: {len(final_message)} chars")
        return final_message

    def _group_messages_by_message_id(self, messages: List[Message]) -> List[List[Message]]:
        """
        Group consecutive messages by their message_id.
        
        This ensures that messages with the same message_id (e.g., tool_use and tool_result)
        stay together and are not split across compression boundaries.
        
        Args:
            messages: List of messages to group
            
        Returns:
            List of message groups, where each group contains consecutive messages
            with the same message_id
        """
        message_groups = []
        current_group = []
        current_group_message_id = None
        
        for msg in messages:
            msg_id = msg.message_id
            
            # Start a new group if:
            # - This is the first message (current_group is empty)
            # - message_id changed
            # - message_id is None (each None message_id gets its own group to avoid
            #   incorrectly grouping unrelated messages)
            if not current_group or msg_id != current_group_message_id or msg_id is None:
                if current_group:
                    message_groups.append(current_group)
                current_group = [msg]
                current_group_message_id = msg_id
            else:
                # Same message_id (and not None), add to current group
                current_group.append(msg)
        
        # Don't forget the last group
        if current_group:
            message_groups.append(current_group)
        
        return message_groups

    async def compact_context_messages(
        self,
        in_context_messages: List[Message]
    ) -> Dict[str, Any]:
        """
        Compress context messages by keeping the latest N messages and compressing all earlier messages.
        
        This method implements a simple compression strategy:
        1. Keep the latest N messages (configurable via keep_recent_messages) uncompressed
        2. Compress all messages before them into a summary
        3. The compacted message is placed as the first message
        
        This approach ensures the model has detailed context of recent activities while
        still having access to older context in summarized form, addressing LLM's
        limited context size constraints.
        
        Args:
            in_context_messages: List of in-context messages
            
        Returns:
            Dictionary with compacted message and success flag
        """
        # Get the number of recent messages to keep from config (default: 10)
        keep_recent_messages = self.compression_config.keep_recent_messages if self.compression_config else 10

        self.logger.info(
            f"[COMPACT_CONTEXT] {len(in_context_messages)} in-context messages, "
            f"keeping latest {keep_recent_messages} messages\n"
        )
        
        # Step 1: Group consecutive messages by message_id to keep related messages together
        # (e.g., tool_use and tool_result pairs should stay together)
        message_groups = self._group_messages_by_message_id(in_context_messages)
        
        self.logger.info(
            f"[COMPACT_CONTEXT] Grouped {len(in_context_messages)} messages into {len(message_groups)} groups by message_id\n"
        )
        
        # Step 2: Find the split point at the group level
        # Count messages from the end to find the split point that keeps at least N messages
        split_group_index = len(message_groups)
        messages_to_keep_count = 0
        
        for i in range(len(message_groups) - 1, -1, -1):
            group = message_groups[i]
            messages_to_keep_count += len(group)
            if messages_to_keep_count >= keep_recent_messages:
                split_group_index = i
                break
        
        # If we haven't accumulated enough messages, keep all of them (no compression needed)
        if messages_to_keep_count < keep_recent_messages or split_group_index == 0:
            self.logger.info(
                f"[COMPACT_CONTEXT] Not enough messages to compress. Total: {len(in_context_messages)}, "
                f"required to keep: {keep_recent_messages}. Skipping compression.\n"
            )
            return {
                "compacted_message": None,
                "success": True,  # Not a failure, just nothing to compress
                "is_all_context_compacted": False,
                "attach_to_id": None,
                "attach_offset_positive": None,
                "token_usage": None
            }
        
        # Step 3: Ensure all tool_result messages in the "keep" section have their corresponding tool_use messages
        # Move split_group_index backward to include any missing tool_use messages
        max_iterations = len(message_groups)  # Prevent infinite loop
        for iteration in range(max_iterations):
            # Collect all tool_use_ids that have tool_result messages in the "keep" range
            tool_result_ids = set()
            for i in range(split_group_index, len(message_groups)):
                for msg in message_groups[i]:
                    if msg.type == "tool_result" and "tool_use_id" in msg.content_core:
                        tool_result_ids.add(msg.content_core["tool_use_id"])
            
            if not tool_result_ids:
                # No tool_result messages in the "keep" range
                break
            
            # Collect all tool_use ids that are already in the "keep" range
            tool_use_ids_in_range = set()
            for i in range(split_group_index, len(message_groups)):
                for msg in message_groups[i]:
                    if msg.type == "tool_use" and "id" in msg.content_core:
                        tool_use_ids_in_range.add(msg.content_core["id"])
            
            # Find tool_result messages whose tool_use is missing
            missing_tool_use_ids = tool_result_ids - tool_use_ids_in_range
            
            if not missing_tool_use_ids:
                # All tool_results have their tool_use messages
                break
            
            # Look backward to find groups containing the missing tool_use messages
            extended = False
            for i in range(split_group_index - 1, -1, -1):
                group = message_groups[i]
                # Check if this group has tool_use messages we need
                found_tool_use_ids = set()
                for msg in group:
                    if msg.type == "tool_use":
                        tool_use_id = msg.content_core.get("id")
                        if tool_use_id in missing_tool_use_ids:
                            found_tool_use_ids.add(tool_use_id)
                
                if found_tool_use_ids:
                    # Include this group by moving split_group_index backward
                    split_group_index = i
                    missing_tool_use_ids -= found_tool_use_ids
                    extended = True
                    
                    # If all missing tool_use messages are found, we can stop
                    if not missing_tool_use_ids:
                        break
            
            # If we didn't extend backward or found all tool_use messages, stop
            if not extended:
                if missing_tool_use_ids:
                    self.logger.warning(
                        f"[COMPACT_CONTEXT] Found {len(missing_tool_use_ids)} tool_result messages without "
                        f"corresponding tool_use messages: {list(missing_tool_use_ids)[:3]}..."
                    )
                break
            
            # Continue iteration in case newly included groups have more tool_results
            if not missing_tool_use_ids:
                break
        
        # Convert group index back to message index
        split_index = sum(len(message_groups[i]) for i in range(split_group_index))
        
        # Messages to compress (earlier messages) and messages to keep (recent messages)
        messages_to_compress = in_context_messages[:split_index]
        messages_to_keep = in_context_messages[split_index:]
        
        self.logger.info(
            f"[COMPACT_CONTEXT] Split at group {split_group_index}/{len(message_groups)}, "
            f"message index {split_index}/{len(in_context_messages)}. "
            f"Compressing {len(messages_to_compress)} messages, keeping {len(messages_to_keep)} messages\n"
        )
        
        # If no messages to compress, skip compression
        if not messages_to_compress:
            self.logger.info("[COMPACT_CONTEXT] No messages to compress. Skipping compression.\n")
            return {
                "compacted_message": None,
                "success": True,
                "is_all_context_compacted": False,
                "attach_to_id": None,
                "attach_offset_positive": None,
                "token_usage": None
            }
        
        # Step 4: Prevent compacting tool_use without tool_result in the messages to compress
        tool_use_ids = set()
        tool_result_ids = set()
        for msg in messages_to_compress:
            if msg.type == "tool_use":
                tool_use_ids.add(msg.content_core.get("id"))
            elif msg.type == "tool_result":
                tool_result_ids.add(msg.content_core.get("tool_use_id"))
        
        pending_ids = tool_use_ids - tool_result_ids
        if pending_ids:
            truncate_idx = len(messages_to_compress)
            for i, msg in enumerate(messages_to_compress):
                if msg.type == "tool_use" and msg.content_core.get("id") in pending_ids:
                    truncate_idx = i
                    break
            
            if truncate_idx < len(messages_to_compress):
                self.logger.info(
                    f"[COMPACT_CONTEXT] Truncating {len(messages_to_compress) - truncate_idx} messages "
                    f"to avoid compacting pending tool calls"
                )
                messages_to_compress = messages_to_compress[:truncate_idx]
        
        # If after truncation there are no messages to compress, skip compression
        if not messages_to_compress:
            self.logger.info("[COMPACT_CONTEXT] No messages to compress after tool call handling. Skipping compression.\n")
            return {
                "compacted_message": None,
                "success": True,
                "is_all_context_compacted": False,
                "attach_to_id": None,
                "attach_offset_positive": None,
                "token_usage": None
            }

        # Step 5: Perform compression using LLM
        compress_dicts = await MessageService.get_llm_compatible_messages(messages_to_compress)
        compacted_result = await self._compact_context_with_llm(compress_dicts)
        compacted_string = compacted_result["compacted_message"]
        token_usage = compacted_result["token_usage"]
        
        if not compacted_string:
            self.logger.error("[COMPACT_CONTEXT] Compact failed, returning original messages")
            return {
                "compacted_message": None,
                "success": False,
                "is_all_context_compacted": False,
                "attach_to_id": None,
                "attach_offset_positive": None,
                "token_usage": token_usage
            }
        
        # Step 6: Create compressed message with references to original messages
        compact_ref_ids = [msg.id for msg in messages_to_compress]
        compacted_string = self.build_context_messages_after_compact(messages_to_compress, compacted_string)

        # The compacted message will be placed as the first message
        # attach_to_id points to the first message of the "keep" section
        # attach_offset_positive=False means the compacted message is placed before attach_to_id
        attach_to_id = messages_to_keep[0].id if messages_to_keep else None
        
        compacted_message = {
            "role": "user",
            "content": [
                {"type": "compacted_message", "text": compacted_string, "ref": compact_ref_ids},
                {"type": "system_reminder", "text": self.sys_reminder_compact},
            ]
        }
        
        self.logger.info(
            f"[COMPACT_CONTEXT] Success: compressed {len(messages_to_compress)} messages into 1, "
            f"keeping {len(messages_to_keep)} recent messages"
        )
        
        return {
            "compacted_message": compacted_message,
            "success": True,
            "is_all_context_compacted": len(messages_to_keep) == 0,
            "attach_to_id": attach_to_id,
            "attach_offset_positive": False,  # Compacted message placed before the first kept message
            "token_usage": token_usage
        }
    
    
    async def _compact_context_with_llm(self, messages_history: List[Dict[str, Any]], max_retries: int = 3) -> Optional[str]:
        """
        Compact conversation context using intelligent LLM-based analysis
        
        Args:
            messages_history: List of agent-format messages with potentially complex content structure
            max_retries: Maximum number of retries when summary_match fails (default: 3)
            
        Returns:
            Compressed message string or None if compression fails
        """
        
        # Prepare system prompt in the required format for AnthropicClient
        system_prompt = [
            {'type': 'text', 'text': self.sys_identity},
            {'type': 'text', 'text': self.sys_compact}
        ]
        
        # Add compression request to message history
        compression_messages = messages_history + [
            {"role": "user", "content": self.user_compact}
        ]
        
        # Retry loop
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                self.logger.info(f"[LLM_COMPACT] Starting attempt {attempt + 1}/{max_retries} for {len(messages_history)} messages\n")
                
                self.logger.info(f"[LLM_COMPACT] Prepared {len(compression_messages)} messages\n")
                
                # Call LLM client in a background thread to avoid blocking the event loop
                self.logger.info("[LLM_COMPACT] Calling LLM for compression\n")

                response, usage = await self.llm_client.call_llm(
                    system_prompt=system_prompt,
                    messages=compression_messages,
                    cache_control=False,
                    business="context_compact_service",
                    thinking_enabled=False
                )
                self.logger.info(f"[LLM_COMPACT] Response: {response}\n")
                
                elapsed_time = time.time() - start_time
                self.logger.info(f"[LLM_COMPACT] LLM call completed in {elapsed_time:.2f}s\n")
                
                # Extract response text from API format
                response_text = ""
                if response and "content" in response:
                    for content in response["content"]:
                        if "type" in content and content["type"] == "text":
                            response_text += content["text"]
                
                # Get token count from usage info
                output_tokens = usage.get("output_tokens", 0)
                self.logger.info(f"[LLM_COMPACT] Completed in {elapsed_time:.2f}s using {output_tokens} tokens\n")
                
                # Parse the compression response
                response_text = response_text.strip()
                
                # Extract analysis and summary content using regex parsing
                self.logger.info("[LLM_COMPACT] Parsing compression response\n")
                summary_match = re.search(r'<summary>(.*?)</summary>', response_text, re.DOTALL)
                
                if summary_match:
                    analysis = response_text[:summary_match.start()].strip()
                    summary = summary_match.group(1).strip()
                    
                    self.logger.info(f"[LLM_COMPACT] Extracted analysis ({len(analysis)} chars) and summary ({len(summary)} chars)")
                    
                    # Format as session continuation message
                    compacted_message = f"### Conversation analysis:\n{analysis}\n\n### Conversation summary:\n{summary}"
                    
                    self.logger.info(f"[LLM_COMPACT] Generated compressed message: {len(compacted_message)} chars")
                    return {
                        "compacted_message": compacted_message,
                        "token_usage": {
                            "token_usage": usage,
                            "business": "compact_context"
                        }
                    }
                else:
                    error_msg = "Failed to extract analysis and summary from compression response"
                    self.logger.error(f"[LLM_COMPACT] Attempt {attempt + 1}/{max_retries}: {error_msg}")
                    self.logger.error(f"[LLM_COMPACT] Found tags - summary: {bool(summary_match)}")
                    self.logger.error(f"[LLM_COMPACT] Response text: {response_text}")
                    
                    # If this is the last attempt, fall back to truncate
                    if attempt == max_retries - 1:
                        self.logger.warning(f"[LLM_COMPACT] All {max_retries} attempts failed, falling back to truncate method\n")
                        return await self._compact_context_with_truncate(messages_history)
                    
                    # Otherwise continue to next retry
                    continue

            except Exception as e:
                error_msg = f"Error in context compact attempt {attempt + 1}/{max_retries}: {e}"
                self.logger.error(f"[LLM_COMPACT] {error_msg}", exc_info=True)
                
                self.logger.warning(f"[LLM_COMPACT] Falling back to truncate method\n")
                return await self._compact_context_with_truncate(messages_history)
        
        # This should never be reached due to the fallback in the last attempt
        self.logger.error("[LLM_COMPACT] Unexpected: exited retry loop without returning")
        return await self._compact_context_with_truncate(messages_history)
    
    async def _compact_context_with_truncate(self, messages_history: List[Dict[str, Any]], max_tokens: int = 16000) -> Dict[str, Any]:
        """
        Simple truncate-based compact that keeps only the last messages within token limit.
        This is a fallback method when LLM-based compact fails.
        
        Args:
            messages_history: List of agent-format messages
            max_tokens: Maximum number of tokens to keep (default: 16000)
            
        Returns:
            Dictionary with compacted message and token usage info
        """
        try:
            self.logger.info(f"[TRUNCATE_COMPACT] Starting truncate compact, keeping last {max_tokens} tokens from {len(messages_history)} total messages\n")
            
            # Traverse messages from the end (most recent) to the beginning
            kept_messages = []
            cumulative_tokens = 0
            
            for i in range(len(messages_history) - 1, -1, -1):
                # Count tokens for this single message
                single_msg = [messages_history[i]]
                msg_tokens = await self.token_counter.count_tokens("", single_msg, None, False)
                
                # Check if adding this message would exceed the token limit
                if cumulative_tokens + msg_tokens <= max_tokens:
                    kept_messages.insert(0, messages_history[i])  # Insert at beginning to maintain order
                    cumulative_tokens += msg_tokens
                else:
                    # Stop if we've exceeded the limit
                    break
            
            removed_count = len(messages_history) - len(kept_messages)
            
            # Create a simple summary message
            summary = f"[Previous conversation truncated: {removed_count} messages removed, keeping last {len(kept_messages)} messages (~{cumulative_tokens} tokens)]"
            
            self.logger.info(f"[TRUNCATE_COMPACT] Truncated {removed_count} messages, kept {len(kept_messages)} messages (~{cumulative_tokens} tokens)\n")
            
            return {
                "compacted_message": summary,
                "token_usage": {
                    "token_usage": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0
                    },
                    "business": "compact_context_truncate"
                }
            }
        except Exception as e:
            self.logger.error(f"[TRUNCATE_COMPACT] Error in truncate compact: {e}", exc_info=True)
            return {
                "compacted_message": None,
                "token_usage": None
            }
    
    async def should_compress(self, messages: List[Dict[str, Any]], system_prompt: str, max_tokens: int, thinking_enabled: bool = False) -> bool:
        """
        Check if context compression is needed based on token count
        
        Args:
            messages: List of messages to count tokens for
            system_prompt: System prompt text
            max_tokens: Maximum token threshold
            thinking_enabled: Whether thinking mode is enabled in conversation
        """
        if not self.token_counter:
            return False
        
        current_tokens = await self.token_counter.count_tokens(system_prompt, messages, self.tools, thinking_enabled)
        return current_tokens > max_tokens

    def update_tools(self, tools: List[Dict[str, Any]]):
        """Update tools list for compression context"""
        self.tools = tools
    