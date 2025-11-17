# CliChat 技术方案（最终版）

## 一、项目概述

**目标**：实现一个轻量级、基于命令行的大模型对话机器人，支持本地模型，类似 Claude Code 的交互体验。

**核心特性**：
- 完全基于 Textual TUI 框架
- 流式输出 + Markdown 渲染 + 代码高亮
- 会话持久化（按 session 分文件）
- 智能上下文管理（懒惰压缩）
- 历史对话搜索和加载

---

## 二、技术栈

| 组件 | 技术选型 | 版本要求 | 说明 |
|------|---------|---------|------|
| UI 框架 | Textual | >=0.47.0 | 现代 TUI 框架 |
| 输出美化 | Rich | >=13.0.0 | Markdown + 代码高亮 |
| HTTP 客户端 | httpx | >=0.25.0 | 异步请求 + 流式响应 |
| 配置解析 | PyYAML + Pydantic | >=6.0 / >=2.0 | 配置验证 |
| 语言检测 | langdetect | >=1.0.9 | 代码块语言识别 |
| Token 计数 | 简单估算 | - | 字符数 / 4 |

**依赖清单** (`requirements.txt`)：
```txt
textual>=0.47.0
rich>=13.0.0
httpx>=0.25.0
pydantic>=2.0.0
PyYAML>=6.0
langdetect>=1.0.9
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

---

## 三、项目结构

```
clichat/
├── clichat/
│   ├── __init__.py
│   ├── __main__.py              # 入口：python -m clichat
│   ├── config.py                # 配置加载与验证
│   ├── llm_client.py            # LLM API 客户端（流式）
│   ├── session_manager.py       # 会话 CRUD + 搜索
│   ├── context_manager.py       # 上下文压缩策略
│   ├── utils.py                 # Token 计数、语言检测等
│   └── ui/
│       ├── __init__.py
│       ├── app.py               # Textual 主应用
│       ├── chat_view.py         # 对话显示区（Markdown）
│       ├── input_bar.py         # 输入框（多行 + 快捷键）
│       ├── session_list.py      # 会话列表侧边栏
│       └── status_bar.py        # 状态栏（Token 计数）
├── tests/
│   ├── test_config.py
│   ├── test_session_manager.py
│   ├── test_llm_client.py
│   ├── test_context_manager.py
│   └── test_e2e.py
├── config.yaml.example          # 配置模板（入 Git）
├── .gitignore                   # 排除 config.yaml
├── requirements.txt
├── README.md
└── CLAUDE.md
```

---

## 四、核心模块设计

### 1. 配置模块 (`config.py`)

**配置文件示例** (`config.yaml.example`)：
```yaml
llm:
  api_base: "http://localhost:11434/v1"  # Ollama 本地地址
  model: "qwen2.5-coder:7b"              # 模型名称
  api_key: "ollama"                      # 本地模型通常不验证
  temperature: 0.7
  max_tokens: 2000
  system_prompt: "You are a helpful AI assistant."

app:
  history_dir: "~/.clichat"         # 对话历史存储目录
  context_strategy: "lazy_compress"      # 上下文管理策略
  compress_threshold: 0.85               # Token 达到 85% 时触发压缩
  compress_summary_tokens: 300           # 压缩后摘要的目标长度
```

**实现要点**：
```python
from pydantic import BaseModel, Field
from pathlib import Path
import yaml

class LLMConfig(BaseModel):
    api_base: str
    model: str
    api_key: str = "ollama"
    temperature: float = 0.7
    max_tokens: int = 2000
    system_prompt: str = "You are a helpful AI assistant."

class AppConfig(BaseModel):
    history_dir: Path
    context_strategy: str = "lazy_compress"
    compress_threshold: float = 0.85
    compress_summary_tokens: int = 300

class Config(BaseModel):
    llm: LLMConfig
    app: AppConfig

def load_config(path: str = "config.yaml") -> Config:
    with open(path) as f:
        data = yaml.safe_load(f)
    config = Config(**data)
    # 展开路径
    config.app.history_dir = Path(config.app.history_dir).expanduser()
    config.app.history_dir.mkdir(parents=True, exist_ok=True)
    return config
```

---

### 2. LLM 客户端 (`llm_client.py`)

**核心功能**：
- 流式请求 OpenAI 兼容 API
- 实时回调每个 chunk
- 错误处理与重试

**接口设计**：
```python
class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        on_chunk: Callable[[str], Awaitable[None]]
    ) -> str:
        """
        流式对话
        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}]
            on_chunk: 回调函数，接收每个生成的文本片段
        Returns:
            完整的回复文本
        """
        url = f"{self.config.api_base}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True
        }

        full_response = ""
        async with self.client.stream("POST", url, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk = parse_sse_chunk(line)  # 解析 SSE
                    if chunk:
                        full_response += chunk
                        await on_chunk(chunk)

        return full_response
```

---

### 3. 会话管理 (`session_manager.py`)

**存储格式** (`~/.clichat/session_20250111_143022.json`)：
```json
{
  "session_id": "20250111_143022",
  "created_at": "2025-01-11T14:30:22",
  "updated_at": "2025-01-11T15:20:10",
  "title": "如何实现二叉树遍历",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant.",
      "timestamp": "2025-01-11T14:30:22",
      "tokens": 8
    },
    {
      "role": "user",
      "content": "如何实现二叉树遍历？",
      "timestamp": "2025-01-11T14:30:25",
      "tokens": 12
    },
    {
      "role": "assistant",
      "content": "二叉树遍历有三种...",
      "timestamp": "2025-01-11T14:30:30",
      "tokens": 156
    }
  ],
  "total_tokens": 176
}
```

**核心方法**：
```python
class SessionManager:
    def __init__(self, history_dir: Path):
        self.history_dir = history_dir

    def create_session(self) -> str:
        """创建新会话，返回 session_id"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        # ...

    def load_session(self, session_id: str) -> Dict:
        """加载指定会话"""
        path = self.history_dir / f"session_{session_id}.json"
        with open(path) as f:
            return json.load(f)

    def list_sessions(self) -> List[Dict]:
        """列出所有会话（按更新时间倒序）"""
        sessions = []
        for path in self.history_dir.glob("session_*.json"):
            with open(path) as f:
                data = json.load(f)
                sessions.append({
                    "session_id": data["session_id"],
                    "title": data["title"],
                    "updated_at": data["updated_at"]
                })
        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)

    def search_sessions(self, keyword: str) -> List[Dict]:
        """全文搜索（标题 + 消息内容）"""
        results = []
        for path in self.history_dir.glob("session_*.json"):
            with open(path) as f:
                data = json.load(f)
                # 搜索标题和所有消息
                if keyword.lower() in data["title"].lower():
                    results.append(data)
                    continue
                for msg in data["messages"]:
                    if keyword.lower() in msg["content"].lower():
                        results.append(data)
                        break
        return results

    def save_message(self, session_id: str, role: str, content: str, tokens: int):
        """追加消息到会话"""
        # 加载 -> 追加 -> 保存
        # 自动更新 updated_at 和 total_tokens
```

---

### 4. 上下文管理 (`context_manager.py`)

**懒惰压缩策略**：

```python
class ContextManager:
    def __init__(self, config: AppConfig, llm_client: LLMClient):
        self.config = config
        self.llm_client = llm_client
        self._compressed_summary = None  # 缓存压缩后的摘要

    async def get_context_messages(
        self,
        session: Dict,
        current_input_tokens: int
    ) -> List[Dict[str, str]]:
        """
        获取用于发送给 LLM 的上下文消息列表

        策略：
        1. 始终保留 system prompt
        2. 如果总 tokens < 阈值：返回全部消息
        3. 如果超过阈值：
           - 保留最近 5-10 条完整消息
           - 将更早的消息压缩成摘要（一次性调用 LLM）
           - 组合：[system] + [摘要] + [最近消息]
        """
        max_tokens = self.config.max_tokens
        threshold = int(max_tokens * self.config.compress_threshold)

        messages = session["messages"]
        system_msg = messages[0]  # system prompt
        history = messages[1:]     # 用户对话

        total_tokens = session["total_tokens"] + current_input_tokens

        # 情况 1：未超过阈值，返回全部
        if total_tokens < threshold:
            return messages

        # 情况 2：需要压缩
        recent_count = 10
        recent_msgs = history[-recent_count:]  # 最近 10 条
        old_msgs = history[:-recent_count]     # 更早的消息

        # 如果还没有压缩过，执行压缩
        if self._compressed_summary is None and old_msgs:
            self._compressed_summary = await self._compress_messages(old_msgs)

        # 组合最终上下文
        result = [system_msg]
        if self._compressed_summary:
            result.append({
                "role": "system",
                "content": f"[Previous conversation summary]\n{self._compressed_summary}"
            })
        result.extend(recent_msgs)

        return result

    async def _compress_messages(self, messages: List[Dict]) -> str:
        """
        调用 LLM 压缩历史消息为摘要
        """
        # 构造压缩提示词
        conversation_text = "\n\n".join([
            f"{msg['role']}: {msg['content']}" for msg in messages
        ])

        compress_prompt = [
            {"role": "system", "content": "You are a conversation summarizer."},
            {"role": "user", "content": f"""
Please summarize the following conversation into {self.config.compress_summary_tokens} tokens or less.
Focus on key information, decisions, and context that would be useful for continuing the conversation.

Conversation:
{conversation_text}

Summary:"""}
        ]

        summary = ""
        async def collect_chunk(chunk: str):
            nonlocal summary
            summary += chunk

        await self.llm_client.chat_stream(compress_prompt, collect_chunk)
        return summary.strip()

    def reset_compression(self):
        """重置压缩缓存（新会话时调用）"""
        self._compressed_summary = None
```

**压缩触发时机**：
- 每次用户发送消息前，检查总 tokens
- 如果超过 85% 阈值且未压缩过，触发一次压缩
- 压缩后可能降到 50-60% 水平，可以继续对话很久
- 整个 session 生命周期内可能只压缩 1-2 次

---

### 5. UI 模块 (Textual)

#### **主应用** (`ui/app.py`)

```python
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer
from textual.binding import Binding

class ChatbotApp(App):
    CSS_PATH = "app.css"
    BINDINGS = [
        Binding("ctrl+c", "quit_check", "Quit", show=False),
        Binding("ctrl+n", "new_session", "New Chat"),
        Binding("ctrl+l", "toggle_sessions", "Sessions"),
        Binding("ctrl+f", "search", "Search"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.llm_client = LLMClient(config.llm)
        self.session_manager = SessionManager(config.app.history_dir)
        self.context_manager = ContextManager(config.app, self.llm_client)
        self.current_session_id = None
        self.last_ctrl_c_time = 0
        self.is_generating = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield SessionList(id="session_list")  # 左侧会话列表
            with Container(id="main"):
                yield ChatView(id="chat_view")    # 对话区
                yield InputBar(id="input_bar")    # 输入框
        yield StatusBar(id="status_bar")          # 状态栏

    async def on_mount(self):
        # 创建新会话
        await self.action_new_session()

    async def action_cancel(self):
        """Esc 中断生成"""
        if self.is_generating:
            self.is_generating = False
            self.notify("Generation cancelled")
```

#### **对话显示区** (`ui/chat_view.py`)

```python
from textual.widgets import RichLog
from rich.markdown import Markdown
from rich.syntax import Syntax

class ChatView(RichLog):
    def append_user_message(self, content: str):
        self.write(Markdown(f"**You:** {content}"))

    def append_assistant_message_start(self):
        self.write("**Assistant:** ", end="")
        self._current_message = ""

    def append_chunk(self, chunk: str):
        """流式追加文本片段"""
        self._current_message += chunk
        # 实时渲染（简化版，实际需要处理 Markdown 边界）
        self.write(chunk, end="")

    def finalize_assistant_message(self):
        """完成后完整渲染 Markdown + 代码高亮"""
        # 清除之前的流式文本，重新渲染完整消息
        self.clear_last_message()
        self.write(Markdown(self._current_message))
```

#### **输入框** (`ui/input_bar.py`)

```python
from textual.widgets import TextArea

class InputBar(TextArea):
    def __init__(self):
        super().__init__(language="markdown")

    async def on_key(self, event):
        if event.key == "ctrl+enter":
            await self.submit_message()

    async def submit_message(self):
        content = self.text.strip()
        if not content:
            return

        # 触发消息发送事件
        self.post_message(MessageSubmitted(content))
        self.clear()
```

---

### 6. 工具函数 (`utils.py`)

```python
def count_tokens(text: str) -> int:
    """简单估算：字符数 / 4"""
    return len(text) // 4

def detect_code_language(code: str) -> str:
    """自动检测代码语言"""
    from langdetect import detect_langs

    # 先尝试关键字匹配
    if "def " in code or "import " in code:
        return "python"
    if "function " in code or "const " in code:
        return "javascript"
    # ... 更多规则

    # 降级到通用检测
    try:
        langs = detect_langs(code)
        return langs[0].lang if langs else "text"
    except:
        return "text"
```

---

## 五、开发步骤与依赖关系

### **Step 1: 基础设施**（2-3 小时）
- [ ] 创建项目结构
- [ ] 实现 `config.py`（配置加载 + Pydantic 验证）
- [ ] 实现 `utils.py`（Token 计数、语言检测）
- [ ] 实现 `session_manager.py`（CRUD + 搜索）
- [ ] 编写单元测试：`test_config.py`, `test_session_manager.py`

**测试要点**：
- 配置文件缺失字段报错
- 路径展开（`~` -> 绝对路径）
- 会话创建、加载、搜索

---

### **Step 2: LLM 集成**（2-3 小时）
- [ ] 实现 `llm_client.py`（流式 API 调用）
- [ ] 实现 SSE 解析
- [ ] 错误处理与重试
- [ ] Mock 测试：`test_llm_client.py`
- [ ] 真实 Ollama 测试（需本地启动 Ollama）

**测试要点**：
- Mock httpx 响应，验证流式解析
- 超时处理
- 错误码处理

---

### **Step 3: 上下文管理**（1-2 小时）
- [ ] 实现 `context_manager.py`（懒惰压缩）
- [ ] 编写测试：`test_context_manager.py`

**测试要点**：
- 未超阈值时返回完整消息
- 超阈值时触发压缩
- 压缩后组合正确

---

### **Step 4: UI 基础框架**（3-4 小时）
- [ ] 实现 `ui/app.py`（主应用框架）
- [ ] 实现 `ui/chat_view.py`（Markdown 渲染）
- [ ] 实现 `ui/input_bar.py`（多行输入 + Ctrl+Enter）
- [ ] 实现 Esc 中断生成

**测试要点**：
- 手动测试 UI 渲染
- 快捷键响应

---

### **Step 5: 功能整合**（3-4 小时）
- [ ] 整合 LLM 流式输出到 ChatView
- [ ] 实现消息发送 -> 保存 -> 显示流程
- [ ] 实现 `ui/session_list.py`（会话列表侧边栏）
- [ ] 实现 `ui/status_bar.py`（Token 计数显示）
- [ ] 实现搜索功能（Ctrl+F）

**测试要点**：
- E2E 测试：创建会话 -> 发送消息 -> 切换会话 -> 搜索

---

### **Step 6: 优化与文档**（1-2 小时）
- [ ] 添加加载动画（生成中显示 spinner）
- [ ] 错误提示优化（网络错误、模型错误）
- [ ] 代码高亮优化（语言自动检测）
- [ ] 编写 README.md（安装、配置、使用）
- [ ] 更新 CLAUDE.md（新增常用命令）

---

## 六、测试策略

### **单元测试**
| 模块 | 测试文件 | 覆盖率目标 |
|------|---------|-----------|
| 配置管理 | `test_config.py` | 90% |
| 会话管理 | `test_session_manager.py` | 85% |
| LLM 客户端 | `test_llm_client.py` | 80% |
| 上下文管理 | `test_context_manager.py` | 85% |

### **集成测试**
- 完整对话流程（Mock LLM）
- 上下文压缩触发
- 会话切换与加载

### **E2E 测试**（需 Ollama 环境）
- 真实模型对话
- 流式输出实时性
- Esc 中断生成

---

## 七、风险与注意事项

### **1. Textual 异步处理**
- Textual 基于 asyncio，所有 LLM 调用必须用 `async/await`
- UI 更新需要在主线程，使用 `call_from_thread` 或 `post_message`

### **2. Windows 路径问题**（已记录在 CLAUDE.md）
- 使用 `Path.expanduser()` 处理 `~`
- JSON 文件路径需转义

### **3. 压缩延迟**
- 首次压缩可能需要 1-2 秒
- 需在 UI 显示"Compressing context..."提示

### **4. 代码高亮边界**
- Markdown 代码块可能在流式输出中被截断
- 需要缓冲完整代码块后再高亮

### **5. Token 计数精度**
- 字符数 / 4 只是估算，误差约 ±20%
- 对于压缩阈值判断足够用

---

## 八、配置示例与使用说明

### **安装**
```bash
cd clichat
pip install -r requirements.txt
cp config.yaml.example config.yaml
# 编辑 config.yaml，配置本地模型地址
```

### **启动**
```bash
python -m clichat
```

### **快捷键**
- `Ctrl+Enter`: 发送消息
- `Ctrl+N`: 新建会话
- `Ctrl+L`: 打开会话列表
- `Ctrl+F`: 搜索历史
- `Esc`: 中断生成
- `Ctrl+C` 双击: 退出应用

---

## 九、方案总结

| 类别 | 内容 |
|------|------|
| **核心依赖** | textual, rich, httpx, pydantic, PyYAML, langdetect |
| **总代码量** | 约 1500-2000 行（含测试） |
| **开发周期** | 12-18 小时（6 个步骤） |
| **关键创新** | 懒惰压缩（低频 LLM 调用）+ 流式 TUI |
| **扩展性** | 易扩展：多模型切换、插件系统、语音输入等 |
