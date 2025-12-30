#!/usr/bin/env python3
"""
Interactive CLI test for Bash-related tools.
Allows testing Bash, BashOutput, LSBash, and KillBash tools interactively.

Usage:
    python interactive_bash_test.py
"""
import asyncio
import sys
import os
import re
import shlex
from typing import Dict, Any, Optional

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_tool_handler import ToolState
from bash_tool import BashToolHandler
from bash_output_tool import BashOutputToolHandler
from ls_bash_tool import LSBashToolHandler
from kill_bash_tool import KillBashToolHandler


class InteractiveBashTester:
    """Interactive tester for Bash tools"""

    def __init__(self):
        # Create a tool state with a test task ID
        self.tool_state = ToolState(
            task_id="interactive-test",
            working_dir=os.getcwd(),
        )

        # Initialize tool handlers
        self.bash_tool = BashToolHandler(self.tool_state)
        self.bash_output_tool = BashOutputToolHandler(self.tool_state)
        self.ls_bash_tool = LSBashToolHandler(self.tool_state)
        self.kill_bash_tool = KillBashToolHandler(self.tool_state)

        self.running = True

    def print_header(self):
        """Print the welcome header"""
        print("\n" + "=" * 70)
        print("Interactive Bash Tools Tester")
        print("=" * 70)
        print("\nAvailable Commands:")
        print("  bash <command>              - Execute a bash command")
        print("  bash <command> --timeout T  - Execute with timeout T seconds")
        print("  bash <command> --session S  - Execute in session S")
        print("  output <session_id>         - Get output from session")
        print("  output <session_id> --filter REGEX - Get filtered output")
        print("  output <session_id> --wait N - Wait N seconds before reading")
        print("  ls                          - List all bash sessions")
        print("  kill <session_id>           - Interrupt session (Ctrl-C)")
        print("  kill <session_id> --end     - Kill entire session")
        print("  help                        - Show this help message")
        print("  quit / exit                 - Exit the tester")
        print("=" * 70 + "\n")

    def print_help(self):
        """Print detailed help"""
        print("\n" + "=" * 70)
        print("DETAILED HELP")
        print("=" * 70)
        print("\n1. BASH TOOL - Execute commands")
        print("   Examples:")
        print("     bash echo 'Hello World'")
        print("     bash ls -la")
        print("     bash sleep 10 --timeout 2")
        print("     bash echo 'Window 1' --session window1")
        print("     bash 'for i in 1 2 3; do echo Line $i; sleep 1; done' --timeout 2")

        print("\n2. BASHOUTPUT TOOL - Get incremental output")
        print("   Examples:")
        print("     output main")
        print("     output main --filter 'error|warning'")
        print("     output build --wait 2")

        print("\n3. LSBASH TOOL - List sessions")
        print("   Examples:")
        print("     ls")

        print("\n4. KILLBASH TOOL - Kill/interrupt sessions")
        print("   Examples:")
        print("     kill main              (sends Ctrl-C)")
        print("     kill build --end       (kills entire session)")

        print("\n" + "=" * 70 + "\n")

    def parse_command(self, line: str) -> tuple:
        """Parse a command line - return both parts and original line"""
        try:
            # Use shlex.split for proper shell-like parsing
            parts = shlex.split(line)
            return parts, line
        except ValueError as e:
            # If shlex fails (e.g., unclosed quotes), fall back to simple split
            print(f"⚠️  Warning: Failed to parse command properly: {e}")
            return line.split(), line

    async def handle_bash_command(self, parts: list, original_line: str):
        """Handle bash command execution - command is passed as-is to bash"""
        if len(parts) < 2:
            print("❌ Error: bash command requires a command to execute")
            print("   Example: bash echo 'Hello World'")
            return

        # Extract options
        timeout = 30.0
        session_id = None
        
        # Parse options from parts
        if '--timeout' in parts:
            idx = parts.index('--timeout')
            if idx + 1 < len(parts):
                try:
                    timeout = float(parts[idx + 1])
                except ValueError:
                    print(f"❌ Error: Invalid timeout value '{parts[idx + 1]}'")
                    return
        
        if '--session' in parts:
            idx = parts.index('--session')
            if idx + 1 < len(parts):
                session_id = parts[idx + 1]
        
        # Extract command from original line by removing 'bash' prefix and options
        # Strategy: remove options from the original string
        command = original_line[4:].strip()  # Remove 'bash' prefix
        
        # Remove --timeout and its value
        if '--timeout' in parts:
            idx = parts.index('--timeout')
            timeout_str = parts[idx + 1] if idx + 1 < len(parts) else ''
            # Find and remove from command string
            pattern = r'--timeout\s+' + re.escape(timeout_str)
            command = re.sub(pattern, '', command, count=1).strip()
        
        # Remove --session and its value
        if '--session' in parts:
            idx = parts.index('--session')
            session_str = parts[idx + 1] if idx + 1 < len(parts) else ''
            # Find and remove from command string
            pattern = r'--session\s+' + re.escape(session_str)
            command = re.sub(pattern, '', command, count=1).strip()

        print(f"\n▶ Executing: {command}")
        if session_id:
            print(f"  Session: {session_id}")
        print(f"  Timeout: {timeout}s")

        try:
            result = await self.bash_tool.execute_async(
                command=command,
                executables=["placeholder"],
                description="placeholder_description",
                wait=timeout,
                session_id=session_id
            )

            status = result.get('display_result', {}).get('status', 'unknown')
            output = result.get('display_result', {}).get('output', '')
            session = result.get('display_result', {}).get('session_id', 'N/A')

            os.makedirs('tmp', exist_ok=True)
            file_number = len(os.listdir('tmp'))
            with open(f'tmp/bash_output_{file_number}.txt', 'w', encoding='utf-8') as bash_output_file:
                bash_output_file.write(await self.tool_state.get_current_cmd_output(session))

            print(f"\n✓ Status: {status} Exit Code: {await self.tool_state.get_last_cmd_exit_code(session)}")
            print(f"  Session ID: {session}")
            if output:
                print(f"\n--- Output ---")
                print(output)
                print("--- End ---")
            else:
                print("  (no output)")

            if status == 'running':
                print(f"\n💡 Tip: Use 'output {session}' to check output later")

        except Exception as e:
            print(f"❌ Error: {e}")

    async def handle_output_command(self, parts: list):
        """Handle output retrieval"""
        if len(parts) < 2:
            print("❌ Error: output command requires a session_id")
            print("   Example: output main")
            return

        session_id = parts[1]
        filter_regex = None
        wait_time = None

        # Parse options
        i = 2
        while i < len(parts):
            if parts[i] == '--filter' and i + 1 < len(parts):
                filter_regex = parts[i + 1]
                i += 2
            elif parts[i] == '--wait' and i + 1 < len(parts):
                try:
                    wait_time = float(parts[i + 1])
                    i += 2
                except ValueError:
                    print(f"❌ Error: Invalid wait value '{parts[i + 1]}'")
                    return
            else:
                i += 1

        print(f"\n▶ Getting output from: {session_id}")
        if filter_regex:
            print(f"  Filter: {filter_regex}")
        if wait_time:
            print(f"  Wait: {wait_time}s")

        try:
            result = await self.bash_output_tool.execute_async(
                session_id=session_id,
                filter=filter_regex,
                wait=wait_time
            )

            status = result.get('display_result', {}).get('status', 'unknown')
            output = result.get('display_result', {}).get('output', '')

            print(f"\n✓ Status: {status}")
            if output:
                print(f"\n--- Output (incremental) ---")
                print(output)
                print("--- End ---")
            else:
                print("  (no new output)")

        except Exception as e:
            print(f"❌ Error: {e}")

    async def handle_ls_command(self):
        """Handle list sessions command"""
        print(f"\n▶ Listing bash sessions...")

        try:
            result = await self.ls_bash_tool.execute_async()

            message = result.get('display_result', {}).get('text', '')
            print(f"\n{message}")

        except Exception as e:
            print(f"❌ Error: {e}")

    async def handle_kill_command(self, parts: list):
        """Handle kill/interrupt command"""
        if len(parts) < 2:
            print("❌ Error: kill command requires a session_id")
            print("   Example: kill main")
            return

        session_id = parts[1]
        end_session = False

        # Parse options
        i = 2
        while i < len(parts):
            if parts[i] == '--end':
                end_session = True
                i += 1
            else:
                i += 1

        action = "Killing" if end_session else "Interrupting"
        print(f"\n▶ {action} session: {session_id}")

        try:
            result = await self.kill_bash_tool.execute_async(
                session_id=session_id,
                end_session=end_session
            )

            message = result.get('display_result', {}).get('text', '')
            print(f"\n✓ {message}")

        except Exception as e:
            print(f"❌ Error: {e}")

    async def handle_command(self, line: str):
        """Handle a user command"""
        line = line.strip()
        if not line:
            return

        parts, original_line = self.parse_command(line)
        if not parts:
            return

        cmd = parts[0].lower()

        if cmd in ('quit', 'exit', 'q'):
            self.running = False
            print("\n👋 Goodbye!")

        elif cmd == 'help' or cmd == 'h':
            self.print_help()

        elif cmd == 'bash':
            await self.handle_bash_command(parts, original_line)

        elif cmd == 'output':
            await self.handle_output_command(parts)

        elif cmd == 'ls':
            await self.handle_ls_command()

        elif cmd == 'kill':
            await self.handle_kill_command(parts)

        else:
            print(f"❌ Unknown command: {cmd}")
            print("   Type 'help' for available commands")

    async def run(self):
        """Run the interactive tester"""
        self.print_header()

        try:
            while self.running:
                try:
                    # Read command from user
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, input, "\n> "
                    )
                    await self.handle_command(line)

                except KeyboardInterrupt:
                    print("\n\n⚠ Interrupted. Type 'quit' to exit.")
                    continue
                except EOFError:
                    break

        finally:
            # Cleanup
            print("\n🧹 Cleaning up...")
            try:
                await self.tool_state.terminate()
            except Exception as e:
                print(f"⚠ Cleanup warning: {e}")


async def main():
    """Main entry point"""
    tester = InteractiveBashTester()
    await tester.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Exiting...")
        sys.exit(0)
