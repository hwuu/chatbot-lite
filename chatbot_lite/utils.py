"""工具函数模块

提供 Token 计数、语言检测等工具函数。
"""

import re
from typing import Optional


def count_tokens(text: str) -> int:
    """
    估算文本的 token 数量

    使用简单的字符数除以 4 的方法进行估算。
    这是一种快速但不精确的方法，误差约 ±20%。

    Args:
        text: 输入文本

    Returns:
        估算的 token 数量
    """
    if not text:
        return 0
    return len(text) // 4


def detect_code_language(code: str) -> str:
    """
    自动检测代码语言

    基于关键字和语法特征进行检测。

    Args:
        code: 代码文本

    Returns:
        检测到的语言名称，如果无法识别则返回 "text"
    """
    if not code or not code.strip():
        return "text"

    code = code.strip()

    # Python
    if re.search(r'\b(def|import|from|class|if __name__|print\()', code):
        return "python"

    # JavaScript/TypeScript
    if re.search(r'\b(function|const|let|var|=>|console\.log)', code):
        if "interface" in code or ": string" in code or ": number" in code:
            return "typescript"
        return "javascript"

    # Java
    if re.search(r'\b(public class|private|protected|void|static|extends)', code):
        return "java"

    # C/C++
    if re.search(r'#include|int main\(|std::|cout|cin', code):
        if "std::" in code or "cout" in code:
            return "cpp"
        return "c"

    # Go
    if re.search(r'\bfunc\s+\w+\(|package\s+\w+|import\s+\(', code):
        return "go"

    # Rust
    if re.search(r'\bfn\s+\w+|let\s+mut|impl\s+\w+|use\s+std::', code):
        return "rust"

    # Ruby
    if re.search(r'\bdef\s+\w+|end\b|puts\s+|require\s+', code):
        return "ruby"

    # PHP
    if code.startswith("<?php") or re.search(r'\$\w+\s*=|function\s+\w+\(', code):
        return "php"

    # Shell/Bash
    if code.startswith("#!") or re.search(r'\b(echo|export|source|bash|sh)\b', code):
        return "bash"

    # SQL
    if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|FROM|WHERE)\b', code, re.IGNORECASE):
        return "sql"

    # HTML
    if re.search(r'<html|<div|<body|<head|<script|<!DOCTYPE', code, re.IGNORECASE):
        return "html"

    # CSS
    if re.search(r'\{[^}]*:[^}]*\}|@media|@import', code):
        return "css"

    # JSON
    if code.startswith("{") or code.startswith("["):
        try:
            import json
            json.loads(code)
            return "json"
        except:
            pass

    # YAML
    if re.search(r'^\w+:\s*$|^\s+-\s+\w+', code, re.MULTILINE):
        return "yaml"

    # Markdown
    if re.search(r'^#{1,6}\s+|^\*\*|^```', code, re.MULTILINE):
        return "markdown"

    # 默认返回 text
    return "text"


def format_timestamp(timestamp: str) -> str:
    """
    格式化时间戳为人类可读的格式

    Args:
        timestamp: ISO 8601 格式的时间戳

    Returns:
        格式化后的时间字符串
    """
    from datetime import datetime

    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本到指定长度

    Args:
        text: 输入文本
        max_length: 最大长度
        suffix: 截断后的后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix
