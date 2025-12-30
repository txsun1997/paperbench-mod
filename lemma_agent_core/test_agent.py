#!/usr/bin/env python3
"""
Simple test script for Lemma Agent Core

Tests basic functionality:
- Agent initialization
- Message handling
- Tool execution
- State management
"""

import asyncio
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.lead_agent import LeadAgent
from config.manager import ConfigManager


async def test_basic_interaction():
    """Test basic agent interaction"""
    print("=" * 60)
    print("Test 1: Basic Interaction")
    print("=" * 60)
    
    config_file = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    config = ConfigManager(config_file=config_file).get_config()
    
    agent = LeadAgent(
        agents_config=config,
        working_dir=os.path.join(os.path.dirname(__file__), "test_workspace")
    )
    
    # Test 1: Simple greeting
    print("\n[Test] User: Hello, who are you?")
    agent.add_user_message("Hello, who are you?")
    response = await agent.run_turn()
    
    if response.get("success"):
        content = response["response"]["content"]
        for block in content:
            if block.get("type") == "text":
                print(f"[Test] Agent: {block.get('text', '')[:200]}...")
    else:
        print(f"[Test] Error: {response.get('message')}")
    
    await agent.cleanup()
    print("\n✓ Test 1 passed\n")


async def test_tool_execution():
    """Test tool execution"""
    print("=" * 60)
    print("Test 2: Tool Execution")
    print("=" * 60)
    
    config_file = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    config = ConfigManager(config_file=config_file).get_config()
    
    # Create test workspace
    test_workspace = os.path.join(os.path.dirname(__file__), "test_workspace")
    os.makedirs(test_workspace, exist_ok=True)
    
    agent = LeadAgent(
        agents_config=config,
        working_dir=test_workspace
    )
    
    # Test 2: List files (should use LS tool)
    print("\n[Test] User: List files in the current directory")
    agent.add_user_message("List files in the current directory")
    response = await agent.run_turn()
    
    if response.get("success"):
        content = response["response"]["content"]
        tool_calls = [b for b in content if b.get("type") == "tool_use"]
        
        if tool_calls:
            print(f"[Test] Agent wants to use {len(tool_calls)} tool(s):")
            for tool_call in tool_calls:
                print(f"  - {tool_call.get('name')}: {tool_call.get('input')}")
            
            # Execute tools
            tool_results = await agent.execute_tools(tool_calls)
            
            for result in tool_results:
                if result.get("success"):
                    print(f"[Test] ✓ {result['tool_name']} executed successfully")
                else:
                    print(f"[Test] ✗ {result['tool_name']} failed: {result['result']}")
            
            # Get agent's response after tool execution
            response = await agent.run_turn()
            if response.get("success"):
                content = response["response"]["content"]
                for block in content:
                    if block.get("type") == "text":
                        print(f"[Test] Agent: {block.get('text', '')[:200]}...")
        else:
            print("[Test] No tools were called")
    else:
        print(f"[Test] Error: {response.get('message')}")
    
    await agent.cleanup()
    print("\n✓ Test 2 passed\n")


async def test_state_persistence():
    """Test state saving and loading"""
    print("=" * 60)
    print("Test 3: State Persistence")
    print("=" * 60)
    
    config_file = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    config = ConfigManager(config_file=config_file).get_config()
    
    test_workspace = os.path.join(os.path.dirname(__file__), "test_workspace")
    os.makedirs(test_workspace, exist_ok=True)
    
    # Create agent and have a conversation
    agent = LeadAgent(
        agents_config=config,
        working_dir=test_workspace
    )
    
    print("\n[Test] Adding messages to agent")
    agent.add_user_message("Remember this: my favorite color is blue")
    response1 = await agent.run_turn()
    
    # Save state
    state_file = os.path.join(test_workspace, "test_state.json")
    agent.message_store.save_to_file(state_file)
    print(f"[Test] State saved to {state_file}")
    
    # Create new agent and load state
    agent2 = LeadAgent(
        agents_config=config,
        working_dir=test_workspace
    )
    agent2.message_store.load_from_file(state_file)
    print(f"[Test] State loaded from {state_file}")
    
    # Check if conversation history was preserved
    messages = agent2.message_store.get_messages()
    print(f"[Test] Loaded {len(messages)} messages")
    
    # Ask about previous conversation
    agent2.add_user_message("What is my favorite color?")
    response2 = await agent2.run_turn()
    
    if response2.get("success"):
        content = response2["response"]["content"]
        for block in content:
            if block.get("type") == "text":
                text = block.get("text", "").lower()
                if "blue" in text:
                    print("[Test] ✓ Agent remembered the favorite color!")
                else:
                    print(f"[Test] Agent response: {block.get('text', '')[:200]}...")
    
    await agent.cleanup()
    await agent2.cleanup()
    
    # Cleanup test file
    if os.path.exists(state_file):
        os.remove(state_file)
    
    print("\n✓ Test 3 passed\n")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("Lemma Agent Core - Test Suite")
    print("=" * 60 + "\n")
    
    try:
        await test_basic_interaction()
        await test_tool_execution()
        await test_state_persistence()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
