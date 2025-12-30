"""
LLM配置 - 统一的LLM相关配置
"""

from typing import Optional
from pydantic import BaseModel, Field, SecretStr, model_validator


class LLMConfig(BaseModel):
    """LLM配置 - 整合所有LLM相关配置"""    
    # Claude API配置
    api_key: Optional[SecretStr] = Field(default=None)
    model: str = Field(default="claude-sonnet-4-20250514")
    base_url: str = Field(default="https://api.yourouter.ai")
    vendor: str = Field(default="anthropic")
    provider: str = Field(default="bedrock")
    
    # AWS Bedrock配置（仅当provider为bedrock时使用）
    aws_access_key: Optional[SecretStr] = Field(default=None, description="AWS Access Key")
    aws_secret_key: Optional[SecretStr] = Field(default=None, description="AWS Secret Key")
    aws_region: Optional[str] = Field(default="us-east-1", description="AWS Region")

    # openrouter API配置
    openrouter_api_key: Optional[SecretStr] = Field(default=None, description="OpenRouter API Key")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1")
    openrouter_model: str = Field(default="anthropic/claude-sonnet-4")

    # 生成参数
    temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=32000, gt=0)
    top_p: Optional[float] = Field(default=None)
    max_context_tokens: int = Field(default=96000, gt=1000)
    
    thinking_budget_tokens: int = Field(
        default=4000,
        gt=0,
        description="思考模式的token预算"
    )
    
    # 重试配置（内置合理默认值）
    num_retries: int = Field(default=5, ge=0)
    retry_multiplier: float = Field(default=2.0, ge=1.0)
    retry_start_wait: int = Field(default=5, gt=0)
    timeout: Optional[int] = Field(default=None)
    
    @model_validator(mode='after')
    def validate_provider_config(self):
        """Validate provider configuration completeness"""
        if self.provider == "anthropic":
            # When provider is anthropic, api_key and model cannot be None
            if self.api_key is None:
                raise ValueError("api_key cannot be None when provider is 'anthropic'")
            if self.model is None:
                raise ValueError("model cannot be None when provider is 'anthropic'")
        elif self.provider == "bedrock":
            # When provider is bedrock, all AWS-related configurations cannot be None
            if self.aws_access_key is None:
                raise ValueError("aws_access_key cannot be None when provider is 'bedrock'")
            if self.aws_secret_key is None:
                raise ValueError("aws_secret_key cannot be None when provider is 'bedrock'")
            if self.aws_region is None:
                raise ValueError("aws_region cannot be None when provider is 'bedrock'")
        return self