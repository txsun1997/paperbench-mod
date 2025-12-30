"""
LLM客户端工厂 - 根据配置创建对应的LLM客户端
"""

from typing import Union

from llm.openrouter_client import OpenRouterClient
from config import LLMConfig, CompressionConfig, PhaseConfig, TokenCountConfig
from llm.anthropic_client import AnthropicClient
from llm.bedrock_client import BedrockClient


def create_llm_client(llm_config: Union[LLMConfig, CompressionConfig, PhaseConfig, TokenCountConfig]):
    """
    根据配置创建对应的LLM客户端
    
    Args:
        llm_config: LLM配置对象，可以是LLMConfig、CompressionConfig、PhaseConfig或TokenCountConfig
        
    Returns:
        对应的客户端实例（AnthropicClient或BedrockClient）
        
    Raises:
        ValueError: 当provider未知时抛出
    """
    if llm_config.provider == "bedrock":
        return BedrockClient(llm_config)
    elif llm_config.provider == "yourouter":
        return AnthropicClient(llm_config)
    elif llm_config.provider == "openrouter":
        return OpenRouterClient(llm_config)
    else:
        raise ValueError(f"Unknown LLM provider: {llm_config.provider}. Supported providers: anthropic, bedrock")

