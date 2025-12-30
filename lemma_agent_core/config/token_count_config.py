"""
Token计数配置 - 统一的Token计数相关配置
"""

from typing import Optional
from pydantic import BaseModel, Field, SecretStr, field_validator


class TokenCountConfig(BaseModel):
    """Token计数配置 - 整合所有Token计数相关配置"""
    
    vendor: str = Field(default="anthropic", description="Model vendor")
    provider: str = Field(default="bedrock", description="API provider")
    
    model: str = Field(default=None, description="AWS Bedrock Model")
    aws_access_key: Optional[SecretStr] = Field(default=None, description="AWS Access Key")
    aws_secret_key: Optional[SecretStr] = Field(default=None, description="AWS Secret Key")
    aws_region: Optional[str] = Field(default=None, description="AWS Region")
    
    # Token计数方法
    method: str = Field(default="estimated", description="Token计数方法: accurate或estimated")

    max_tokens: int = Field(default=128000)

    max_retries: int = Field(default=4, ge=1)
    
    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate method field must be 'accurate' or 'estimated'"""
        if v not in ['accurate', 'estimated']:
            raise ValueError(f"method must be 'accurate' or 'estimated', but got '{v}'")
        return v

