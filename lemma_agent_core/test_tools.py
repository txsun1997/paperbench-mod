#!/usr/bin/env python3
"""
Test script for LocalToolExecutor with real toolkit handlers
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from tools.local_tool_executor import LocalToolExecutor


async def test_read_tool():
    """Test Read tool"""
    print("\n=== Testing Read Tool ===")
    executor = LocalToolExecutor('.', 'test_read')
    
    # Create a test file
    test_file = os.path.abspath("test_read.txt")
    with open(test_file, 'w') as f:
        f.write("Hello World!\nThis is a test file.\n")
    
    # Test reading the file
    result = await executor.execute_tool("Read", {"file_path": test_file})
    print(f"Success: {result['success']}")
    print(f"Result preview: {result['result'][:100]}...")
    
    # Cleanup
    os.remove(test_file)
    await executor.cleanup()
    return result['success']


async def test_write_tool():
    """Test Write tool"""
    print("\n=== Testing Write Tool ===")
    executor = LocalToolExecutor('.', 'test_write')
    
    test_file = os.path.abspath("test_write.txt")
    content = "This is written by Write tool!\nLine 2\n"
    
    # Test writing a file
    result = await executor.execute_tool("Write", {
        "file_path": test_file,
        "content": content
    })
    print(f"Success: {result['success']}")
    
    # Verify the file was created
    if os.path.exists(test_file):
        with open(test_file, 'r') as f:
            written_content = f.read()
        print(f"File created: {written_content == content}")
        os.remove(test_file)
    
    await executor.cleanup()
    return result['success']


async def test_bash_tool():
    """Test Bash tool"""
    print("\n=== Testing Bash Tool ===")
    executor = LocalToolExecutor('.', 'test_bash')
    
    # Test simple bash command
    result = await executor.execute_tool("Bash", {
        "command": "echo 'Hello from Bash'",
        "executables": ["echo"],
        "tool_id": "test_bash_1"
    })
    print(f"Success: {result['success']}")
    print(f"Result: {result['result'][:200]}")
    
    await executor.cleanup()
    return result['success']


async def test_ls_tool():
    """Test LS tool"""
    print("\n=== Testing LS Tool ===")
    executor = LocalToolExecutor('.', 'test_ls')
    
    # List current directory
    result = await executor.execute_tool("LS", {"path": os.path.abspath(".")})
    print(f"Success: {result['success']}")
    print(f"Result preview: {result['result'][:200]}...")
    
    await executor.cleanup()
    return result['success']


async def test_glob_tool():
    """Test Glob tool"""
    print("\n=== Testing Glob Tool ===")
    executor = LocalToolExecutor('.', 'test_glob')
    
    # Find all Python files
    result = await executor.execute_tool("Glob", {"pattern": "*.py"})
    print(f"Success: {result['success']}")
    print(f"Found files preview: {result['result'][:200]}...")
    
    await executor.cleanup()
    return result['success']


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing LocalToolExecutor with Real Toolkit Handlers")
    print("=" * 60)
    
    tests = [
        ("Read Tool", test_read_tool),
        ("Write Tool", test_write_tool),
        ("Bash Tool", test_bash_tool),
        ("LS Tool", test_ls_tool),
        ("Glob Tool", test_glob_tool),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results[test_name] = "✓ PASSED" if success else "✗ FAILED"
        except Exception as e:
            results[test_name] = f"✗ ERROR: {str(e)[:50]}"
            print(f"Error: {e}")
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    for test_name, result in results.items():
        print(f"{test_name:20s}: {result}")
    
    # Summary
    passed = sum(1 for r in results.values() if "PASSED" in r)
    total = len(results)
    print(f"\nSummary: {passed}/{total} tests passed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
