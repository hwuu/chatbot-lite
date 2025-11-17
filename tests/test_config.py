"""config.py 的单元测试"""

import tempfile
from pathlib import Path

import pytest
import yaml

from clichat.config import Config, LLMConfig, AppConfig, load_config


class TestLLMConfig:
    """测试 LLMConfig"""

    def test_valid_config(self):
        """测试有效配置"""
        config = LLMConfig(
            api_base="http://localhost:11434/v1",
            model="qwen2.5-coder:7b",
            api_key="ollama",
            temperature=0.7,
            max_tokens=2000,
            system_prompt="You are a helpful assistant.",
        )
        assert config.api_base == "http://localhost:11434/v1"
        assert config.model == "qwen2.5-coder:7b"
        assert config.temperature == 0.7

    def test_default_values(self):
        """测试默认值"""
        config = LLMConfig(api_base="http://test", model="test-model")
        assert config.api_key == "ollama"
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.system_prompt == "You are a helpful AI assistant."

    def test_temperature_validation(self):
        """测试温度范围验证"""
        # 有效范围
        LLMConfig(api_base="http://test", model="test", temperature=0.0)
        LLMConfig(api_base="http://test", model="test", temperature=2.0)

        # 超出范围
        with pytest.raises(ValueError):
            LLMConfig(api_base="http://test", model="test", temperature=-0.1)
        with pytest.raises(ValueError):
            LLMConfig(api_base="http://test", model="test", temperature=2.1)

    def test_max_tokens_validation(self):
        """测试 max_tokens 验证（必须 > 0）"""
        LLMConfig(api_base="http://test", model="test", max_tokens=1)

        with pytest.raises(ValueError):
            LLMConfig(api_base="http://test", model="test", max_tokens=0)
        with pytest.raises(ValueError):
            LLMConfig(api_base="http://test", model="test", max_tokens=-100)


class TestAppConfig:
    """测试 AppConfig"""

    def test_valid_config(self):
        """测试有效配置"""
        config = AppConfig(
            history_dir="~/.clichat",
            context_strategy="lazy_compress",
            compress_threshold=0.85,
            compress_summary_tokens=300,
        )
        assert config.history_dir == "~/.clichat"
        assert config.context_strategy == "lazy_compress"

    def test_default_values(self):
        """测试默认值"""
        config = AppConfig(history_dir="/tmp/test")
        assert config.context_strategy == "lazy_compress"
        assert config.compress_threshold == 0.85
        assert config.compress_summary_tokens == 300
        assert config.markdown_code_theme == "monokai"

    def test_strategy_validation(self):
        """测试策略验证"""
        # 有效策略
        AppConfig(history_dir="/tmp/test", context_strategy="lazy_compress")
        AppConfig(history_dir="/tmp/test", context_strategy="sliding_window")

        # 无效策略
        with pytest.raises(ValueError, match="context_strategy 必须是"):
            AppConfig(history_dir="/tmp/test", context_strategy="invalid_strategy")

    def test_threshold_validation(self):
        """测试阈值范围验证"""
        # 有效范围
        AppConfig(history_dir="/tmp/test", compress_threshold=0.0)
        AppConfig(history_dir="/tmp/test", compress_threshold=1.0)

        # 超出范围
        with pytest.raises(ValueError):
            AppConfig(history_dir="/tmp/test", compress_threshold=-0.1)
        with pytest.raises(ValueError):
            AppConfig(history_dir="/tmp/test", compress_threshold=1.1)

    def test_markdown_code_theme_validation(self):
        """测试 Markdown 代码主题验证"""
        # 有效主题
        AppConfig(history_dir="/tmp/test", markdown_code_theme="monokai")
        AppConfig(history_dir="/tmp/test", markdown_code_theme="github-dark")
        AppConfig(history_dir="/tmp/test", markdown_code_theme="dracula")

        # 无效主题
        with pytest.raises(ValueError, match="不是有效的主题"):
            AppConfig(history_dir="/tmp/test", markdown_code_theme="invalid_theme_xyz")


class TestLoadConfig:
    """测试 load_config 函数"""

    def test_auto_create_default_config(self, tmp_path, capsys):
        """测试配置文件不存在时自动创建默认配置"""
        config_file = tmp_path / "auto_generated_config.yaml"

        # 确保文件不存在
        assert not config_file.exists()

        # 加载配置（应该自动创建）
        config = load_config(str(config_file))

        # 验证文件已创建
        assert config_file.exists()

        # 验证配置包含所有必需字段（使用默认值）
        assert config.llm.api_base == "http://localhost:11434/v1"
        assert config.llm.model == "qwen2.5:7b"
        assert config.llm.api_key == "ollama"
        assert config.llm.temperature == 0.7
        assert config.llm.max_tokens == 2000
        assert config.app.context_strategy == "lazy_compress"
        assert config.app.compress_threshold == 0.85
        assert config.app.compress_summary_tokens == 300
        assert config.app.markdown_code_theme == "monokai"

        # 验证输出了提示信息
        captured = capsys.readouterr()
        assert "首次运行" in captured.out
        assert "已创建默认配置文件" in captured.out

    def test_load_valid_config(self, tmp_path):
        """测试加载有效配置"""
        # 创建临时配置文件
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {
                "api_base": "http://localhost:11434/v1",
                "model": "qwen2.5-coder:7b",
                "api_key": "test-key",
                "temperature": 0.8,
                "max_tokens": 3000,
                "system_prompt": "Test prompt",
            },
            "app": {
                "history_dir": str(tmp_path / "history"),
                "context_strategy": "lazy_compress",
                "compress_threshold": 0.9,
                "compress_summary_tokens": 400,
            },
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # 加载配置
        config = load_config(str(config_file))

        assert config.llm.api_base == "http://localhost:11434/v1"
        assert config.llm.model == "qwen2.5-coder:7b"
        assert config.llm.temperature == 0.8
        assert config.app.context_strategy == "lazy_compress"
        assert config.app.compress_threshold == 0.9

    def test_path_expansion(self, tmp_path):
        """测试路径展开（~ -> 绝对路径）"""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "llm": {
                "api_base": "http://localhost:11434/v1",
                "model": "test-model",
            },
            "app": {"history_dir": "~/.clichat-test"},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        config = load_config(str(config_file))

        # 验证路径已展开为绝对路径
        assert not config.app.history_dir.startswith("~")
        assert Path(config.app.history_dir).is_absolute()

    def test_history_dir_creation(self, tmp_path):
        """测试自动创建历史目录"""
        config_file = tmp_path / "config.yaml"
        history_dir = tmp_path / "test_history"

        config_data = {
            "llm": {
                "api_base": "http://localhost:11434/v1",
                "model": "test-model",
            },
            "app": {"history_dir": str(history_dir)},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        # 确保目录不存在
        assert not history_dir.exists()

        # 加载配置
        config = load_config(str(config_file))

        # 验证目录已创建
        assert Path(config.app.history_dir).exists()
        assert Path(config.app.history_dir).is_dir()

    def test_missing_required_fields(self, tmp_path):
        """测试缺失必填字段"""
        config_file = tmp_path / "config.yaml"

        # 缺失 llm.api_base
        config_data = {
            "llm": {"model": "test-model"},
            "app": {"history_dir": "/tmp/test"},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError):
            load_config(str(config_file))

    def test_invalid_field_values(self, tmp_path):
        """测试无效字段值"""
        config_file = tmp_path / "config.yaml"

        # temperature 超出范围
        config_data = {
            "llm": {
                "api_base": "http://test",
                "model": "test-model",
                "temperature": 3.0,  # 超出范围
            },
            "app": {"history_dir": "/tmp/test"},
        }

        with open(config_file, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError):
            load_config(str(config_file))
