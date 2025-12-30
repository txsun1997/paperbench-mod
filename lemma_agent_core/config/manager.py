"""
配置管理器 - 负责配置加载
"""

import os
import yaml
from typing import Optional
from pathlib import Path

from .agents_config import AgentsConfig
from monitor import AgentLogger


class ConfigManager:
    """配置管理器 - 精简版"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._find_config_file()
        self._config: Optional[AgentsConfig] = None
        self.logger = AgentLogger()
    
    def _find_config_file(self) -> str:
        """查找配置文件"""
        candidates = [
            "config.yaml",
            "agents/config.yaml"
        ]
        
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        
        # 如果找不到配置文件，返回默认路径（会使用默认值）
        return "config.yaml"
    
    def load_config(self) -> AgentsConfig:
        """加载配置"""
        if self._config is not None:
            return self._config
        
        # 1. 加载YAML配置
        config_data = {}
        if Path(self.config_file).exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    raw_data = yaml.safe_load(f)
                    if raw_data:
                        config_data = raw_data
            except Exception as e:
                error_msg = f"Failed to load config file {self.config_file}: {e}"
                raise RuntimeError(error_msg) from e
        
        # 2. 创建配置对象（Pydantic会自动使用默认值）
        try:
            self._config = AgentsConfig(**config_data)
        except Exception as e:
            # 配置验证失败是关键错误，需要记录到日志
            error_msg = f"Configuration validation failed: {e}"
            raise ValueError(error_msg) from e
        
        # 3. 设置AWS环境变量（用于token count）
        config = getattr(self._config, 'token_count')
        if config.method == 'accurate':
            if config.aws_access_key is None or config.aws_secret_key is None:
                raise ValueError(
                    "AWS credentials (aws_access_key and aws_secret_key) are required "
                    "when token_count.method is set to 'accurate'"
                )
            os.environ["AWS_ACCESS_KEY_ID"] = config.aws_access_key.get_secret_value()
            os.environ["AWS_SECRET_ACCESS_KEY"] = config.aws_secret_key.get_secret_value()        
        
        return self._config
    
    def get_config(self) -> AgentsConfig:
        """获取配置实例"""
        return self.load_config()