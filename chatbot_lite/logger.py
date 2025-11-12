"""日志配置模块"""

import logging
import os
from pathlib import Path

# 全局 logger 字典，避免重复创建
_loggers = {}


def setup_logger(log_dir: str = None, force: bool = False):
    """
    设置日志系统

    Args:
        log_dir: 日志目录路径，默认为 ~/.chatbot-lite/logs/
        force: 强制重新设置（用于测试）
    """
    # 配置根 logger
    root_logger = logging.getLogger("chatbot_lite")

    # 如果已经有 handlers 且不是强制重新设置，则跳过
    if root_logger.handlers and not force:
        return

    # 清除已有的 handlers（避免重复添加）
    root_logger.handlers.clear()

    # 设置日志级别
    root_logger.setLevel(logging.INFO)

    # 确定日志目录
    if log_dir is None:
        log_dir = os.path.expanduser("~/.chatbot-lite/logs")

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 日志文件路径
    log_file = log_path / "app.log"

    # 创建文件 handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    # 设置日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] [%(filename)s:%(lineno)d] %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    # 添加 handler 到根 logger
    root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    获取 logger 实例

    Args:
        name: logger 名称（通常使用 __name__）

    Returns:
        Logger 实例
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(f"chatbot_lite.{name}")

    return _loggers[name]
