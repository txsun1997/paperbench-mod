# Lemma Agent Core

Simplified, stateful version of Lemma Agent for research and development.

## Overview

This is a standalone version of Lemma Agent with all backend dependencies removed. It's designed for:
- **Research**: Easy to understand and modify core agent logic
- **Development**: Rapid iteration on agent algorithms
- **Testing**: Simple local testing without backend infrastructure

## Key Features

- **Stateful**: Agent maintains conversation history across turns
- **Self-contained**: No backend, WebSocket, or remote services required
- **Simple**: Clean code structure, easy to understand and modify
- **Complete**: Full agent capabilities including tools, memory management, and LLM integration

## Architecture

```
lemma_agent_core/
├── agent/              # Core agent logic
│   ├── base_agent.py   # Base agent with stateful conversation
│   └── lead_agent.py   # Main agent implementation
├── llm/                # LLM clients (Anthropic, Bedrock, OpenAI)
├── memory/             # Memory management and compression
├── tools/              # Tool definitions and executors
├── message/            # Local message storage
├── prompts/            # System prompts
├── config/             # Configuration management
└── runner.py           # Interactive CLI runner
```

## Quick Start

### 1. Installation

```bash
cd lemma_agent_core
pip install -r requirements.txt
```

### 2. Configuration

Edit `config/config.yaml` to set your LLM credentials:

```yaml
llm:
  provider: "bedrock"  # or "anthropic" or "openrouter"
  vendor: "anthropic"
  model: "claude-sonnet-4"
  # ... add your API keys
```

### 3. Run

```bash
python runner.py
```

## Usage

### Interactive Mode

```bash
python runner.py
```

Commands:
- Type your message and press Enter to chat
- `exit` or `quit`: Exit the program
- `clear`: Clear conversation history
- `save <file>`: Save conversation state to file
- `load <file>`: Load conversation state from file

### Programmatic Usage

```python
import asyncio
from agent.lead_agent import LeadAgent
from config.manager import ConfigManager

async def main():
    # Initialize agent
    config = ConfigManager("config/config.yaml").get_config()
    agent = LeadAgent(
        agents_config=config,
        working_dir="./workspace"
    )
    
    # Add user message
    agent.add_user_message("List files in the current directory")
    
    # Execute one turn
    response = await agent.run_turn()
    
    # Handle tool calls if any
    if response.get("success"):
        content = response["response"]["content"]
        tool_calls = [b for b in content if b.get("type") == "tool_use"]
        if tool_calls:
            await agent.execute_tools(tool_calls)
            response = await agent.run_turn()
    
    print(response)
    
    # Cleanup
    await agent.cleanup()

asyncio.run(main())
```

## Differences from Production Lemma

### Removed
- WebSocket communication
- RemoteMessageService and backend APIs
- Distributed task scheduling
- Backend state synchronization
- SII-specific features

### Simplified
- Message storage (now local in-memory)
- Tool execution (direct local calls)
- System info gathering (uses local system info)
- Configuration (removed backend-related config)

### Added
- LocalMessageStore for in-memory state
- LocalToolExecutor for direct tool execution
- Simple CLI runner for interactive testing
- State save/load functionality

## Development

### Adding New Tools

1. Create tool definition in `tools/your_tool/tool.py`:
```python
from tools.base_tool import BaseTool

class YourTool(BaseTool):
    @property
    def name(self) -> str:
        return "YourTool"
    
    @property
    def input_schema(self) -> dict:
        return {...}
```

2. Create tool handler in `tools/handlers/your_tool.py`:
```python
from tools.handlers.base_tool_handler import BaseToolHandler

class YourToolHandler(BaseToolHandler):
    async def execute_async(self, **kwargs):
        # Implementation
        return {"result": "...", "display_result": {...}}
```

3. Register in `tools/local_tool_executor.py`

### Modifying Agent Behavior

Core agent logic is in:
- `agent/base_agent.py`: Main conversation loop, tool execution, memory management
- `agent/lead_agent.py`: System prompt initialization
- `memory/memory_manager.py`: Context compression

### Testing

```bash
pytest tests/
```

## Configuration

Key config options in `config/config.yaml`:

```yaml
llm:
  provider: "bedrock"           # LLM provider
  model: "claude-sonnet-4"      # Model name
  max_tokens: 32000             # Max output tokens
  max_context_tokens: 96000     # Context window size
  temperature: 1.0              # Sampling temperature

compression:
  keep_recent_messages: 10      # Messages to keep after compression

token_count:
  method: "accurate"            # Token counting method
  max_token: 128000             # Max context size
```

## Troubleshooting

### Import Errors

Make sure you're running from the `lemma_agent_core` directory:
```bash
cd lemma_agent_core
python runner.py
```

### LLM API Errors

Check your API credentials in `config/config.yaml`. For Bedrock, ensure AWS credentials are properly configured.

### Tool Execution Errors

Check that tool handlers are properly imported in `tools/local_tool_executor.py` and that ToolState is initialized correctly.

## License

Same as original Lemma project.

## Acknowledgments

This is a research-focused refactoring of the production Lemma Agent, designed to make the core algorithm accessible and easy to iterate on.
