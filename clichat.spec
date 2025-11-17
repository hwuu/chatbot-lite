# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置文件

用于将 CliChat 打包为独立可执行文件。

构建命令：
    pyinstaller clichat.spec

输出目录：
    dist/clichat/  # one-folder 模式
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
root_dir = Path.cwd()

# 主程序入口
a = Analysis(
    ['clichat/__main__.py'],
    pathex=[str(root_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'textual',
        'textual.app',
        'textual.widgets',
        'textual.containers',
        'textual.binding',
        'textual.message',
        'textual.events',
        'rich',
        'rich.text',
        'rich.markdown',
        'openai',
        'pydantic',
        'yaml',
        'langdetect',
        'pyperclip',
        'pygments',
        'pygments.styles',
        'pygments.lexers',
        'tiktoken',  # openai 依赖
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'pytest-asyncio',
        'unittest',
        'test',
        'tests',
        '_pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# One-Folder 模式（适合普通用户，便于调试）
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='clichat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 终端应用
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='clichat',
)
