"""配置管理模块

负责加载和验证 config.yaml 配置文件。
"""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    """LLM 配置"""

    api_base: str = Field(..., description="API 基础地址")
    model: str = Field(..., description="模型名称")
    api_key: str = Field(default="ollama", description="API 密钥")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: int = Field(default=2000, gt=0, description="最大 token 数")
    system_prompt: str = Field(
        default="You are a helpful AI assistant.", description="系统提示词"
    )


class AppConfig(BaseModel):
    """应用配置"""

    history_dir: str = Field(..., description="对话历史存储目录")
    context_strategy: str = Field(
        default="lazy_compress", description="上下文管理策略"
    )
    compress_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="压缩阈值（占 max_tokens 的比例）"
    )
    compress_summary_tokens: int = Field(
        default=300, gt=0, description="压缩后摘要的目标长度"
    )

    @field_validator("context_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """验证上下文管理策略"""
        allowed = ["lazy_compress", "sliding_window"]
        if v not in allowed:
            raise ValueError(f"context_strategy 必须是 {allowed} 之一")
        return v


class Config(BaseModel):
    """完整配置"""

    llm: LLMConfig
    app: AppConfig


def load_config(config_path: str = "config.yaml") -> Config:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径，默认为 config.yaml

    Returns:
        Config: 配置对象

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置验证失败
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {path.absolute()}\n"
            f"请复制 config.yaml.example 并重命名为 config.yaml"
        )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    config = Config(**data)

    # 展开路径（~ -> 绝对路径）
    history_dir = Path(config.app.history_dir).expanduser().absolute()
    config.app.history_dir = str(history_dir)

    # 创建历史目录
    history_dir.mkdir(parents=True, exist_ok=True)

    return config
