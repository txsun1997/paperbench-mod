import uuid
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
import time


class Message:
    """
    Simplified Message class for local agent usage.
    
    Stores conversation messages with core content and metadata,
    without backend-specific fields.
    """
    
    def __init__(
        self,
        role: Literal["user", "assistant"],
        type: Literal["text", "image", "document", "system_reminder", "compacted_message", "tool_use", "tool_result", "thinking"],
        content_core: Dict[str, Any] = None,
        id: str = None,
        message_id: str = None,
        gmt_create: int = None,
        token_usage: Dict[str, Any] = None
    ):
        """
        Initialize a Message.
        
        Args:
            role: "user" or "assistant"
            type: Message type (text, tool_use, tool_result, etc.)
            content_core: Core content dictionary
            id: Unique message ID
            message_id: Group ID for related messages (e.g., tool_use + tool_result)
            gmt_create: Creation timestamp in milliseconds
            token_usage: Token usage information for this message
        """
        self.role = role
        self.type = type
        self.id = id if id else str(uuid.uuid4())
        self.message_id = message_id
        self.gmt_create = gmt_create if gmt_create else int(time.time() * 1000)
        self.content_core = content_core if content_core is not None else {}
        self.token_usage = token_usage if token_usage is not None else {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for storage/serialization"""
        return {
            "role": self.role,
            "type": self.type,
            "id": self.id,
            "message_id": self.message_id,
            "gmt_create": self.gmt_create,
            "content_core": self.content_core,
            "token_usage": self.token_usage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create a Message from a dictionary"""
        return cls(
            role=data.get("role"),
            type=data.get("type"),
            content_core=data.get("content_core", {}),
            id=data.get("id"),
            message_id=data.get("message_id"),
            gmt_create=data.get("gmt_create"),
            token_usage=data.get("token_usage", {})
        )
    
    def __repr__(self) -> str:
        return f"Message(role={self.role}, type={self.type}, id={self.id[:8]}...)"
