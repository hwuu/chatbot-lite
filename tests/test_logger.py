"""logger.py 的单元测试"""

import logging
import os
from pathlib import Path

import pytest

from chatbot_lite.logger import get_logger, setup_logger


class TestLogger:
    """测试日志配置"""

    def test_setup_logger_creates_log_directory(self, tmp_path):
        """测试 setup_logger 创建日志目录"""
        log_dir = tmp_path / "logs"
        setup_logger(str(log_dir), force=True)

        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_setup_logger_creates_log_file(self, tmp_path):
        """测试 setup_logger 创建日志文件"""
        log_dir = tmp_path / "logs"
        setup_logger(str(log_dir), force=True)

        log_file = log_dir / "app.log"

        # 写入一条日志
        logger = get_logger(__name__)
        logger.info("Test message")

        # 验证日志文件存在且有内容
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Test message" in content

    def test_logger_format(self, tmp_path):
        """测试日志格式是否符合预期"""
        log_dir = tmp_path / "logs"
        setup_logger(str(log_dir), force=True)

        logger = get_logger(__name__)
        logger.info("Format test")

        log_file = log_dir / "app.log"
        content = log_file.read_text(encoding="utf-8")

        # 验证格式包含：时间戳、文件名、行号、级别、消息
        assert "[test_logger.py:" in content
        assert "] INFO - Format test" in content

    def test_logger_level_info(self, tmp_path):
        """测试日志级别为 INFO"""
        log_dir = tmp_path / "logs"
        setup_logger(str(log_dir), force=True)

        logger = get_logger(__name__)
        logger.debug("Debug message")
        logger.info("Info message")

        log_file = log_dir / "app.log"
        content = log_file.read_text(encoding="utf-8")

        # DEBUG 级别不应该被记录
        assert "Debug message" not in content
        # INFO 级别应该被记录
        assert "Info message" in content

    def test_logger_records_warning_and_error(self, tmp_path):
        """测试日志记录 WARNING 和 ERROR 级别"""
        log_dir = tmp_path / "logs"
        setup_logger(str(log_dir), force=True)

        logger = get_logger(__name__)
        logger.warning("Warning message")
        logger.error("Error message")

        log_file = log_dir / "app.log"
        content = log_file.read_text(encoding="utf-8")

        assert "WARNING - Warning message" in content
        assert "ERROR - Error message" in content

    def test_get_logger_returns_same_instance(self, tmp_path):
        """测试 get_logger 返回同一个 logger 实例"""
        log_dir = tmp_path / "logs"
        setup_logger(str(log_dir), force=True)

        logger1 = get_logger("test")
        logger2 = get_logger("test")

        assert logger1 is logger2

    def test_setup_logger_default_directory(self):
        """测试 setup_logger 使用默认目录"""
        # 不传参数，使用默认目录
        setup_logger(force=True)

        # 验证可以获取 logger
        logger = get_logger(__name__)
        assert logger is not None
        # 验证 effective level 是 INFO
        assert logger.getEffectiveLevel() == logging.INFO
