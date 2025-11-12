"""配置管理模块

负责加载和验证 config.yaml 配置文件。
"""

import os
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
    markdown_code_theme: str = Field(
        default="monokai", description="Markdown 代码块主题"
    )

    @field_validator("context_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """验证上下文管理策略"""
        allowed = ["lazy_compress", "sliding_window"]
        if v not in allowed:
            raise ValueError(f"context_strategy 必须是 {allowed} 之一")
        return v

    @field_validator("markdown_code_theme")
    @classmethod
    def validate_code_theme(cls, v: str) -> str:
        """验证 Markdown 代码主题"""
        # 获取所有可用主题
        try:
            from pygments.styles import get_all_styles
            available_themes = list(get_all_styles())
            if v not in available_themes:
                raise ValueError(
                    f"markdown_code_theme '{v}' 不是有效的主题。"
                    f"可用主题: {', '.join(sorted(available_themes))}"
                )
        except ImportError:
            # 如果 pygments 未安装，跳过验证
            pass
        return v


class Config(BaseModel):
    """完整配置"""

    llm: LLMConfig
    app: AppConfig


# 默认配置模板
DEFAULT_CONFIG_TEMPLATE = """# Chatbot-Lite 配置文件
# 首次运行自动生成，请根据需要修改

llm:
  api_base: "http://localhost:11434/v1"    # Ollama API 地址
  model: "qwen2.5:7b"                       # 模型名称
  api_key: "ollama"                         # API 密钥（Ollama 默认为 "ollama"）
  temperature: 0.7                          # 生成温度（0.0-2.0）
  max_tokens: 2000                          # 最大 token 数
  system_prompt: "You are a helpful AI assistant."  # 系统提示词

app:
  history_dir: "~/.chatbot-lite/history"    # 对话历史存储目录
  context_strategy: "lazy_compress"         # 上下文管理策略
  compress_threshold: 0.85                  # Token 达到 85% 时触发压缩
  compress_summary_tokens: 300              # 压缩后摘要的目标长度
  markdown_code_theme: "monokai"            # Markdown 代码块主题
"""


def get_default_config_path() -> Path:
    """
    获取默认配置文件路径

    Returns:
        Path: ~/.chatbot-lite/config.yaml
    """
    return Path.home() / ".chatbot-lite" / "config.yaml"


def create_default_config(config_path: Optional[Path] = None) -> Path:
    """
    创建默认配置文件

    Args:
        config_path: 配置文件路径，默认为 ~/.chatbot-lite/config.yaml

    Returns:
        Path: 创建的配置文件路径
    """
    if config_path is None:
        config_path = get_default_config_path()

    # 创建目录
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入默认配置
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG_TEMPLATE)

    return config_path


def load_config(config_path: Optional[str] = None) -> Config:
    """
    加载配置文件

    首次运行时会自动创建默认配置文件到 ~/.chatbot-lite/config.yaml

    Args:
        config_path: 配置文件路径，默认为 ~/.chatbot-lite/config.yaml

    Returns:
        Config: 配置对象

    Raises:
        ValueError: 配置验证失败
    """
    # 确定配置文件路径
    if config_path is None:
        path = get_default_config_path()
    else:
        path = Path(config_path)

    # 如果配置文件不存在，创建默认配置
    if not path.exists():
        # 首次运行，创建默认配置
        path = create_default_config(path)
        print(f"首次运行，已创建默认配置文件: {path}")
        print("请编辑配置文件以设置您的 LLM API 信息")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    config = Config(**data)

    # 展开路径（~ -> 绝对路径）
    history_dir = Path(config.app.history_dir).expanduser().absolute()
    config.app.history_dir = str(history_dir)

    # 创建历史目录
    history_dir.mkdir(parents=True, exist_ok=True)

    return config
