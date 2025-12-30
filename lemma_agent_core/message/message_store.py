from typing import List, Dict, Any
from .message import Message
import json


class LocalMessageStore:
    """
    Local message storage for stateful agent operation.
    
    Replaces RemoteMessageService by maintaining messages, todos, and plan
    in memory for the lifetime of the agent.
    """
    
    def __init__(self):
        self.messages: List[Message] = []
        self.todos: List[Dict[str, Any]] = []
        self.plan: str = ""
    
    def add_message(self, message: Message) -> None:
        """Add a message to the store"""
        self.messages.append(message)
    
    def get_messages(self) -> List[Message]:
        """Get all messages"""
        return self.messages
    
    def get_messages_dict(self) -> List[Dict[str, Any]]:
        """Get all messages as dictionaries (for LLM compatibility)"""
        return [msg.to_dict() for msg in self.messages]
    
    def update_todos(self, todos: List[Dict[str, Any]]) -> None:
        """Update the todos list"""
        self.todos = todos
    
    def get_todos(self) -> List[Dict[str, Any]]:
        """Get current todos"""
        return self.todos
    
    def update_plan(self, plan: str) -> None:
        """Update the plan"""
        self.plan = plan
    
    def get_plan(self) -> str:
        """Get current plan"""
        return self.plan
    
    def clear(self) -> None:
        """Clear all stored data"""
        self.messages = []
        self.todos = []
        self.plan = ""
    
    def save_to_file(self, filepath: str) -> None:
        """Save state to a JSON file"""
        state = {
            "messages": [msg.to_dict() for msg in self.messages],
            "todos": self.todos,
            "plan": self.plan
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str) -> None:
        """Load state from a JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        self.messages = [Message.from_dict(msg) for msg in state.get("messages", [])]
        self.todos = state.get("todos", [])
        self.plan = state.get("plan", "")
