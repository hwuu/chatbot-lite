# CliChat

<div align="center">

**轻量级命令行大模型对话机器人**

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-74%20passed-brightgreen.svg)](tests/)

一个功能强大的终端聊天应用，支持本地大模型（Ollama）和 OpenAI API，提供流畅的对话体验。

</div>

---

## ✨ 核心特性

### 🎨 现代化终端界面
- **基于 Textual 框架**：流畅的 TUI 体验，支持鼠标和键盘操作
- **实时 Markdown 渲染**：消息支持富文本格式、代码高亮、表格等
- **流式输出**：实时显示 AI 回复，带打字机效果
- **代码语法高亮**：自动识别代码语言，支持多种主题

### 💬 智能对话管理
- **会话持久化**：所有对话自动保存到本地 JSON 文件
- **全文搜索**：快速搜索历史对话内容和标题
- **智能上下文压缩**：超过 Token 限制时自动压缩历史消息
- **会话列表**：侧边栏显示所有会话，支持快速切换

### ⚡ 便捷操作
- **输入历史导航**：`Ctrl+Up/Down` 快速调用历史输入
- **一键复制**：`Ctrl+Y` 复制最后一条 AI 回复
- **中断生成**：`Ctrl+C` 随时中断 AI 输出
- **退出确认**：`Ctrl+Q` 退出前二次确认，防止误操作

### 🔧 灵活配置
- **多模型支持**：兼容 OpenAI API、Ollama 本地模型等
- **自定义主题**：支持多种 UI 和代码主题
- **参数可调**：温度、最大 Token、系统提示词等均可配置

---

## 📦 安装

### 环境要求
- Python 3.10 或更高版本
- 支持 Windows、macOS、Linux

### 快速安装

```bash
# 克隆仓库
git clone https://github.com/hwuu/clichat.git
cd clichat

# 安装依赖
pip install -r requirements.txt

# 复制配置文件模板
cp config.yaml.example config.yaml

# 编辑配置（设置你的模型地址）
# 使用你喜欢的编辑器打开 config.yaml
```

---

## 🚀 快速开始

### 1. 配置模型

编辑 `config.yaml` 文件：

```yaml
llm:
  api_base: "http://localhost:11434/v1"  # Ollama 本地地址
  model: "qwen2.5-coder:7b"              # 模型名称
  api_key: "ollama"                      # 本地模型通常不验证
  temperature: 0.7                       # 生成温度
  max_tokens: 2000                       # 最大 token 数
  system_prompt: "You are a helpful AI assistant."

app:
  history_dir: "~/.clichat"              # 对话历史存储目录
  context_strategy: "lazy_compress"      # 上下文管理策略
  compress_threshold: 0.85               # 达到 85% 时触发压缩
  compress_summary_tokens: 300           # 压缩后摘要长度
  markdown_code_theme: "github-dark"     # 代码块主题
  ui_theme: "textual-dark"               # UI 主题
```

**使用 Ollama（推荐）：**
```bash
# 安装 Ollama（见 https://ollama.ai）
ollama pull qwen2.5-coder:7b  # 或其他模型
```

**使用 OpenAI API：**
```yaml
llm:
  api_base: "https://api.openai.com/v1"
  model: "gpt-4"
  api_key: "你的 API Key"
```

### 2. 启动应用

```bash
python -m clichat
```

首次运行会在 `~/.clichat/` 目录创建默认配置文件和历史记录。

---

## 🎮 使用指南

### 快捷键

| 快捷键 | 功能 | 说明 |
|--------|------|------|
| `Ctrl+N` | 新建会话 | 创建一个新的对话会话 |
| `Ctrl+L` | 切换会话列表 | 显示/隐藏左侧会话列表 |
| `Ctrl+F` | 搜索会话 | 全文搜索历史对话 |
| `Ctrl+Y` | 复制回复 | 复制最后一条 AI 消息到剪贴板 |
| `Ctrl+C` | 中断生成 | 停止当前 AI 输出 |
| `Ctrl+Q` | 退出应用 | 退出前会二次确认 |
| `Ctrl+Enter` | 发送消息 | 发送输入框中的消息 |
| `Ctrl+Up/Down` | 历史输入 | 导航输入历史记录 |
| `Delete` | 删除会话 | 删除选中的会话（需确认） |

### 主要功能

#### 1️⃣ 发送消息
在底部输入框输入消息，按 `Ctrl+Enter` 发送。支持多行输入。

#### 2️⃣ 会话管理
- **新建**：`Ctrl+N` 创建新会话
- **切换**：点击左侧会话列表或使用 `Ctrl+L` 切换
- **搜索**：`Ctrl+F` 打开搜索对话框，输入关键词搜索
- **删除**：选中会话后按 `Delete` 键

#### 3️⃣ 复制内容
- **复制 AI 回复**：`Ctrl+Y` 快速复制最后一条消息
- **复制代码块**：鼠标选中后使用系统复制快捷键

#### 4️⃣ 中断输出
AI 生成过程中按 `Ctrl+C` 可随时中断，UI 保持响应。

---

## 🏗️ 项目结构

```
clichat/
├── clichat/                    # 主包
│   ├── __init__.py
│   ├── __main__.py            # 程序入口
│   ├── config.py              # 配置加载与验证
│   ├── llm_client.py          # LLM 客户端（流式 + 中断）
│   ├── session_manager.py     # 会话 CRUD + 搜索
│   ├── context_manager.py     # 上下文智能压缩
│   ├── logger.py              # 日志系统
│   ├── utils.py               # 工具函数
│   └── ui/                    # UI 组件
│       ├── app.py             # 主应用
│       ├── chat_view.py       # 对话显示区
│       ├── input_bar.py       # 输入框（多行 + 历史）
│       ├── session_list.py    # 会话列表
│       ├── search_screen.py   # 搜索对话框
│       ├── quit_screen.py     # 退出确认
│       └── status_bar.py      # 状态栏
├── tests/                     # 单元测试（74 个测试）
├── docs/                      # 设计文档
├── config.yaml.example        # 配置模板
├── requirements.txt           # 依赖列表
├── build.py                   # 打包脚本
└── clichat.spec              # PyInstaller 配置
```

---

## 🧪 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 查看测试覆盖率
python -m pytest tests/ --cov=clichat --cov-report=html
```

当前测试状态：**74 个测试全部通过** ✅

---

## 📦 打包分发

使用 PyInstaller 打包为独立可执行文件：

```bash
# 运行构建脚本
python build.py

# 输出目录
dist/clichat/
├── clichat.exe        # Windows
├── clichat            # macOS/Linux
└── README.txt
```

打包后的程序可直接运行，无需 Python 环境。

---

## 🎨 自定义主题

### UI 主题
在 `config.yaml` 中设置：
- `textual-dark`（默认）
- `nord`
- `gruvbox`
- `monokai`
- `dracula`
- `tokyo-night`

### 代码主题
支持的代码高亮主题：
- `github-dark`（默认）
- `dracula`
- `one-dark`
- `solarized-dark`
- `nord`
- `monokai`

---

## 🛠️ 技术栈

- **UI 框架**: [Textual](https://textual.textualize.io/) - 现代化终端用户界面
- **LLM 客户端**: [OpenAI Python SDK](https://github.com/openai/openai-python) - 支持流式输出
- **Markdown 渲染**: Textual 内置 Markdown 组件
- **数据验证**: [Pydantic](https://docs.pydantic.dev/) - 配置模型
- **测试框架**: [pytest](https://pytest.org/) + pytest-asyncio

---

## 🤝 贡献指南

欢迎贡献代码、报告 Bug 或提出功能建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 开源协议

本项目采用 [MIT License](LICENSE) 开源协议。

---

## 🙏 致谢

- [Textual](https://textual.textualize.io/) - 提供强大的终端 UI 框架
- [Ollama](https://ollama.ai/) - 简化本地大模型部署
- [OpenAI](https://openai.com/) - 提供标准化 API 接口

---

## 📬 联系方式

- GitHub Issues: [提交问题](https://github.com/hwuu/clichat/issues)
- 项目主页: [https://github.com/hwuu/clichat](https://github.com/hwuu/clichat)

---

<div align="center">

**如果觉得有用，请给个 ⭐ Star！**

Made with ❤️ by hwuu

</div>
