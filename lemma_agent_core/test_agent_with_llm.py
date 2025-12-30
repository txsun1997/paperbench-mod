#!/usr/bin/env python3
"""
Test Agent with real LLM (AWS Bedrock)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from agent.lead_agent import LeadAgent
from config.manager import ConfigManager


async def test_simple_task():
    """Test a simple task with the agent"""
    print("=" * 60)
    print("Testing Lemma Agent Core with AWS Bedrock")
    print("=" * 60)
    
    # Load config
    config = ConfigManager('config.yaml').get_config()
    print(f"✓ Config loaded: {config.llm.provider} / {config.llm.model}")
    
    # Create agent
    agent = LeadAgent(
        agents_config=config,
        working_dir=os.getcwd(),
        task_id="test_task_1"
    )
    print("✓ Agent initialized")
    
    # Test 1: Simple question
    print("\n" + "=" * 60)
    print("Test 1: Ask agent to list files")
    print("=" * 60)
    
    agent.add_user_message("List all Python files in the current directory")
    print("✓ User message added")
    
    print("Calling LLM...")
    response = await agent.run_turn()
    print(f"\n✓ Response received")
    print(f"Role: {response.get('role')}")
    print(f"Stop reason: {response.get('stop_reason')}")
    
    # Check if there are tool calls
    content = response.get('response', {}).get('content', [])
    tool_calls = [block for block in content if block.get('type') == 'tool_use']
    text_blocks = [block for block in content if block.get('type') == 'text']
    
    if text_blocks:
        print(f"\nAgent text response:")
        for block in text_blocks:
            print(f"  {block.get('text', '')[:200]}...")
    
    if tool_calls:
        print(f"\n✓ Agent wants to use {len(tool_calls)} tool(s):")
        for tool_call in tool_calls:
            print(f"  - {tool_call.get('name')}: {tool_call.get('input')}")
        
        # Execute tools
        print("\nExecuting tools...")
        tool_results = await agent.execute_tools(tool_calls)
        print(f"✓ Tools executed: {len(tool_results)} results")
        
        # Get final response
        print("\nGetting final response...")
        final_response = await agent.run_turn()
        final_content = final_response.get('response', {}).get('content', [])
        final_text = [block for block in final_content if block.get('type') == 'text']
        
        if final_text:
            print(f"\nFinal agent response:")
            for block in final_text:
                print(f"  {block.get('text', '')}")
    
    print("\n" + "=" * 60)
    print("✓ Test completed successfully!")
    print("=" * 60)
    
    # Cleanup
    await agent.cleanup()


async def main():
    try:
        await test_simple_task()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
