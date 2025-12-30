#!/usr/bin/env python3
"""
Simple interactive runner for Lemma Agent Core

This is a basic runner for testing and development. It provides:
- Interactive command-line interface
- Stateful conversation (agent persists across turns)
- Automatic tool execution
- Simple output display
"""

import asyncio
import os
import sys
from typing import Dict, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.lead_agent import LeadAgent
from config.manager import ConfigManager


def print_response(response: Dict[str, Any]):
    """Print agent response in a readable format"""
    if not response.get("success"):
        print(f"\n❌ Error: {response.get('message', 'Unknown error')}\n")
        return
    
    content = response.get("response", {}).get("content", [])
    
    for block in content:
        block_type = block.get("type")
        
        if block_type == "text":
            text = block.get("text", "")
            print(f"\n{text}\n")
        
        elif block_type == "thinking":
            # Optionally display thinking (can be toggled)
            thinking = block.get("thinking", "")
            print(f"\n💭 Thinking: {thinking[:200]}...\n" if len(thinking) > 200 else f"\n💭 Thinking: {thinking}\n")
        
        elif block_type == "tool_use":
            tool_name = block.get("name")
            tool_input = block.get("input", {})
            print(f"\n🔧 Using tool: {tool_name}")
            print(f"   Input: {tool_input}\n")


async def main():
    """Main interactive loop"""
    # Get config file path
    config_file = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    
    if not os.path.exists(config_file):
        print(f"Error: Config file not found at {config_file}")
        print("Please ensure config.yaml exists in the config directory.")
        return
    
    # Initialize config
    try:
        config = ConfigManager(config_file=config_file).get_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # Set working directory (current directory by default)
    working_dir = os.getcwd()
    
    # Create agent (stateful - persists across conversation)
    print("Initializing Lemma Agent...")
    try:
        agent = LeadAgent(
            agents_config=config,
            working_dir=working_dir
        )
        print("✓ Agent initialized successfully\n")
    except Exception as e:
        print(f"Error initializing agent: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("=" * 60)
    print("Lemma Agent Core - Interactive Mode")
    print("=" * 60)
    print(f"Working directory: {working_dir}")
    print("\nType your message and press Enter.")
    print("Type 'exit' or 'quit' to exit.")
    print("Type 'clear' to clear conversation history.")
    print("Type 'save <file>' to save conversation state.")
    print("Type 'load <file>' to load conversation state.")
    print("=" * 60)
    print()
    
    try:
        while True:
            # Get user input
            try:
                user_input = input("You: ").strip()
            except EOFError:
                print("\nExiting...")
                break
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ['exit', 'quit']:
                print("Goodbye!")
                break
            
            elif user_input.lower() == 'clear':
                agent.message_store.clear()
                print("✓ Conversation history cleared\n")
                continue
            
            elif user_input.lower().startswith('save '):
                filepath = user_input[5:].strip()
                try:
                    agent.message_store.save_to_file(filepath)
                    print(f"✓ Conversation saved to {filepath}\n")
                except Exception as e:
                    print(f"❌ Error saving: {e}\n")
                continue
            
            elif user_input.lower().startswith('load '):
                filepath = user_input[5:].strip()
                try:
                    agent.message_store.load_from_file(filepath)
                    print(f"✓ Conversation loaded from {filepath}\n")
                except Exception as e:
                    print(f"❌ Error loading: {e}\n")
                continue
            
            # Add user message to agent
            agent.add_user_message(user_input)
            
            # Execute conversation turn
            print("\nAgent: ", end="", flush=True)
            
            try:
                # Run one turn
                response = await agent.run_turn()
                
                # Print response
                print_response(response)
                
                # If response contains tool calls, execute them and continue
                if response.get("success"):
                    content = response.get("response", {}).get("content", [])
                    tool_calls = [block for block in content if block.get("type") == "tool_use"]
                    
                    if tool_calls:
                        # Execute tools
                        tool_results = await agent.execute_tools(tool_calls)
                        
                        # Print tool results
                        for result in tool_results:
                            if result.get("success"):
                                print(f"   ✓ {result['tool_name']}: {result['result'][:100]}...")
                            else:
                                print(f"   ❌ {result['tool_name']}: {result['result']}")
                        
                        # Continue conversation after tool execution
                        print("\nAgent: ", end="", flush=True)
                        response = await agent.run_turn()
                        print_response(response)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user\n")
                continue
            except Exception as e:
                print(f"\n❌ Error during execution: {e}\n")
                import traceback
                traceback.print_exc()
    
    finally:
        # Cleanup
        print("\nCleaning up...")
        await agent.cleanup()
        print("Done.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
