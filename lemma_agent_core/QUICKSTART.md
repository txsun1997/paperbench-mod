# Lemma Agent Core - Quick Start Guide

## 5分钟快速上手

### 1. 安装依赖（1分钟）

```bash
cd lemma_agent_core
pip install -r requirements.txt
```

### 2. 配置LLM（2分钟）

编辑 `config/config.yaml`，设置你的API密钥：

**使用Anthropic Claude**:
```yaml
llm:
  provider: "anthropic"  
  vendor: "anthropic"
  api_key: "your-api-key-here"
  model: "claude-3-5-sonnet-20241022"
```

**使用AWS Bedrock**:
```yaml
llm:
  provider: "bedrock"
  vendor: "anthropic"
  aws_access_key: "your-access-key"
  aws_secret_key: "your-secret-key"
  aws_region: "us-east-1"
  model: "anthropic.claude-sonnet-4-20250514-v1:0"
```

### 3. 运行测试（1分钟）

```bash
python test_agent.py
```

如果看到 "All tests passed! ✓"，说明配置成功！

### 4. 开始使用（1分钟）

```bash
python runner.py
```

尝试这些命令：
```
You: Hello, who are you?
You: What files are in the current directory?
You: Create a file called test.txt with content "Hello World"
```

## 常见问题

### Q: Import错误
A: 确保在lemma_agent_core目录下运行：
```bash
cd lemma_agent_core
python runner.py
```

### Q: API密钥错误
A: 检查config/config.yaml中的密钥是否正确设置

### Q: 工具执行失败
A: 这是正常的，部分高级工具可能需要额外配置。基础工具（Read、Write、LS等）应该可以正常工作。

## 下一步

- 查看 `README.md` 了解详细功能
- 查看 `IMPLEMENTATION_NOTES.md` 了解架构细节
- 查看 `PROJECT_SUMMARY.md` 了解完整实现

## 最简示例代码

```python
import asyncio
from agent.lead_agent import LeadAgent
from config.manager import ConfigManager

async def main():
    config = ConfigManager("config/config.yaml").get_config()
    agent = LeadAgent(config, ".")
    
    agent.add_user_message("Hello!")
    response = await agent.run_turn()
    
    print(response["response"]["content"][0]["text"])
    await agent.cleanup()

asyncio.run(main())
```

就这么简单！🎉
