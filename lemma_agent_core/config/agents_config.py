"""
Agents服务完整配置
"""

from pydantic import BaseModel, Field

from .llm_config import LLMConfig
from .compression_config import CompressionConfig
from .phase_config import PhaseConfig
from .token_count_config import TokenCountConfig


class AgentsConfig(BaseModel):
    """Agents服务完整配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    compression: CompressionConfig = Field(default_factory=CompressionConfig)
    phase: PhaseConfig = Field(default_factory=PhaseConfig)
    token_count: TokenCountConfig = Field(default_factory=TokenCountConfig)