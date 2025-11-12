#!/usr/bin/env python
"""Chatbot-Lite 构建脚本

用于将应用打包为独立可执行文件。

使用方法：
    python build.py

支持平台：
    - Windows (exe)
    - macOS (app)
    - Linux (bin)

输出目录：
    dist/chatbot-lite/
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def check_pyinstaller():
    """检查 PyInstaller 是否已安装"""
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} 已安装")
        return True
    except ImportError:
        print("✗ PyInstaller 未安装")
        print("正在安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("✓ PyInstaller 安装完成")
        return True


def clean_build():
    """清理构建目录"""
    print("\n[1/4] 清理构建目录...")

    dirs_to_clean = ["build", "dist"]
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"  删除 {dir_name}/")
            shutil.rmtree(dir_path)

    print("✓ 清理完成")


def run_tests():
    """运行测试"""
    print("\n[2/4] 运行测试...")

    result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], capture_output=True, text=True)

    if result.returncode == 0:
        print("✓ 所有测试通过")
        return True
    else:
        print("✗ 测试失败")
        print(result.stdout)
        print(result.stderr)
        return False


def build_executable():
    """构建可执行文件"""
    print("\n[3/4] 构建可执行文件...")
    print(f"  平台: {platform.system()}")
    print(f"  架构: {platform.machine()}")

    # 运行 PyInstaller
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "chatbot-lite.spec", "--clean"],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✓ 构建完成")
        return True
    else:
        print("✗ 构建失败")
        print(result.stdout)
        print(result.stderr)
        return False


def create_readme():
    """创建发布说明"""
    print("\n[4/4] 创建发布说明...")

    system = platform.system()
    machine = platform.machine()

    if system == "Windows":
        exe_name = "chatbot-lite.exe"
    elif system == "Darwin":  # macOS
        exe_name = "chatbot-lite"
    else:  # Linux
        exe_name = "chatbot-lite"

    readme_content = f"""# Chatbot-Lite

终端聊天机器人应用

## 系统信息

- 平台: {system}
- 架构: {machine}
- Python 版本: {sys.version.split()[0]}

## 使用方法

### Windows
```bash
chatbot-lite.exe
```

### macOS / Linux
```bash
./chatbot-lite
```

## 配置

首次运行时，程序会自动在用户目录创建配置文件：

```
~/.chatbot-lite/config.yaml
```

请编辑此文件以设置：
- LLM API 地址 (api_base)
- 模型名称 (model)
- API 密钥 (api_key)
- 其他参数

## 快捷键

- Ctrl+J: 发送消息
- Ctrl+N: 新建对话
- Ctrl+L: 显示/隐藏会话列表
- Ctrl+F: 搜索历史对话
- Ctrl+Y: 复制最后一条回复
- Esc: 中断生成
- Ctrl+Q: 退出程序

## 数据存储

对话历史保存在：
```
~/.chatbot-lite/history/
```

## 支持

GitHub: https://github.com/hwuu/chatbot-lite
"""

    readme_path = Path("dist/chatbot-lite/README.txt")
    readme_path.write_text(readme_content, encoding="utf-8")
    print(f"✓ 创建 {readme_path}")


def main():
    """主函数"""
    print("=" * 60)
    print("  Chatbot-Lite 构建工具")
    print("=" * 60)

    # 检查 PyInstaller
    if not check_pyinstaller():
        print("\n✗ 构建失败: 无法安装 PyInstaller")
        sys.exit(1)

    # 清理
    clean_build()

    # 运行测试
    if not run_tests():
        response = input("\n测试失败，是否继续构建？(y/N): ")
        if response.lower() != 'y':
            print("✗ 构建已取消")
            sys.exit(1)

    # 构建
    if not build_executable():
        print("\n✗ 构建失败")
        sys.exit(1)

    # 创建说明
    create_readme()

    # 完成
    print("\n" + "=" * 60)
    print("  构建完成！")
    print("=" * 60)
    print(f"\n可执行文件位置: dist/chatbot-lite/")

    system = platform.system()
    if system == "Windows":
        print("运行命令: dist\\chatbot-lite\\chatbot-lite.exe")
    else:
        print("运行命令: dist/chatbot-lite/chatbot-lite")

    print("\n提示: 首次运行会自动创建配置文件 ~/.chatbot-lite/config.yaml")


if __name__ == "__main__":
    main()
