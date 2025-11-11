"""主应用"""

import time

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header

from chatbot_lite.config import Config, load_config
from chatbot_lite.context_manager import ContextManager
from chatbot_lite.llm_client import LLMClient
from chatbot_lite.session_manager import SessionManager
from chatbot_lite.ui.chat_view import ChatView
from chatbot_lite.ui.input_bar import InputBar, MessageSubmitted
from chatbot_lite.ui.search_screen import SearchScreen
from chatbot_lite.ui.session_list import SessionList, SessionSelected
from chatbot_lite.ui.status_bar import StatusBar
from chatbot_lite.utils import count_tokens


class ChatbotApp(App):
    """Chatbot-Lite 主应用"""

    CSS = """
    Screen {
        background: $surface;
    }

    #main {
        height: 100%;
        width: 100%;
    }

    #chat_container {
        width: 1fr;
        height: 100%;
    }

    #chat_view {
        height: 1fr;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }

    #chat_view .message-content {
        margin-left: 2;
    }

    #input_bar {
        height: auto;
        border: solid $accent;
        margin: 1;
        padding: 1;
    }

    #status_bar {
        dock: bottom;
        height: 1;
        background: $boost;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit_check", "Quit", show=False),
        Binding("ctrl+n", "new_session", "New Chat", show=True),
        Binding("ctrl+l", "toggle_sessions", "Sessions", show=True),
        Binding("ctrl+f", "search", "Search", show=True),
        Binding("ctrl+y", "copy_last_message", "Copy", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.config: Config = None
        self.llm_client: LLMClient = None
        self.session_manager: SessionManager = None
        self.context_manager: ContextManager = None
        self.current_session_id: str = None
        self.last_ctrl_c_time: float = 0
        self.is_generating: bool = False

    def compose(self) -> ComposeResult:
        """组合 UI 组件"""
        yield Header()
        with Container(id="main"):
            with Horizontal():
                yield SessionList(id="session_list")
                with Vertical(id="chat_container"):
                    yield ChatView(id="chat_view")
                    yield InputBar(id="input_bar")
        yield StatusBar(id="status_bar")
        yield Footer()

    async def on_mount(self):
        """应用挂载时初始化"""
        try:
            # 加载配置
            self.config = load_config()

            # 初始化组件
            self.llm_client = LLMClient(self.config.llm)
            self.session_manager = SessionManager(self.config.app.history_dir)
            self.context_manager = ContextManager(
                self.config.app, self.llm_client
            )

            # 创建新会话
            await self.action_new_session()

            # 显示欢迎消息
            chat_view = self.query_one("#chat_view", ChatView)
            chat_view.append_system_message(
                "Welcome to Chatbot-Lite! Type your message and press Ctrl+D to send (Enter for new line)."
            )

            # 聚焦到输入框
            input_bar = self.query_one("#input_bar", InputBar)
            input_bar.focus()

        except FileNotFoundError as e:
            # 配置文件不存在
            chat_view = self.query_one("#chat_view", ChatView)
            chat_view.append_error_message(str(e))
            self.exit()
        except Exception as e:
            # 其他初始化错误
            chat_view = self.query_one("#chat_view", ChatView)
            chat_view.append_error_message(f"Initialization error: {e}")
            self.exit()

    async def action_quit_check(self):
        """双击 Ctrl-C 退出"""
        now = time.time()
        if now - self.last_ctrl_c_time < 1.0:
            # 关闭 LLM 客户端
            if self.llm_client:
                await self.llm_client.close()
            self.exit()
        else:
            self.last_ctrl_c_time = now
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.set_status("Press Ctrl+C again to quit")

    async def action_cancel(self):
        """Esc 中断生成"""
        if self.is_generating:
            self.is_generating = False
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.set_status("Generation cancelled")

    async def action_copy_last_message(self):
        """Ctrl+Y 复制最后一条助手消息"""
        chat_view = self.query_one("#chat_view", ChatView)
        last_message = chat_view.get_last_assistant_message()

        if not last_message:
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.set_status("No message to copy")
            return

        try:
            import pyperclip
            pyperclip.copy(last_message)
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.set_status("Message copied to clipboard")
        except ImportError:
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.set_status("pyperclip not installed. Run: pip install pyperclip")
        except Exception as e:
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.set_status(f"Copy failed: {e}")

    async def action_new_session(self):
        """创建新会话"""
        self.current_session_id = self.session_manager.create_session(
            self.config.llm.system_prompt
        )
        self.context_manager.reset_compression()

        # 更新状态栏
        session = self.session_manager.load_session(self.current_session_id)
        status_bar = self.query_one("#status_bar", StatusBar)
        status_bar.update_session(
            self.current_session_id, session["title"], session["total_tokens"]
        )
        status_bar.set_status("New session created")

        # 更新会话列表
        self._refresh_session_list()

    async def action_toggle_sessions(self):
        """切换会话列表显示/隐藏"""
        session_list = self.query_one("#session_list", SessionList)
        session_list.toggle_visibility()

        # 如果显示会话列表，刷新列表
        if not session_list.has_class("hidden"):
            self._refresh_session_list()

    async def action_search(self):
        """打开搜索对话框"""
        search_screen = SearchScreen(self.session_manager)
        result = await self.push_screen(search_screen)

        # 如果用户选择了会话，加载该会话
        if result:
            await self._load_session(result)

    def _refresh_session_list(self):
        """刷新会话列表"""
        sessions = self.session_manager.list_sessions()
        session_list = self.query_one("#session_list", SessionList)
        session_list.update_sessions(sessions)

    async def _load_session(self, session_id: str):
        """
        加载指定会话

        Args:
            session_id: 会话 ID
        """
        try:
            # 加载会话
            session = self.session_manager.load_session(session_id)
            self.current_session_id = session_id

            # 重置上下文管理器
            self.context_manager.reset_compression()

            # 清空当前对话显示
            chat_view = self.query_one("#chat_view", ChatView)
            chat_view.clear_chat()

            # 显示会话消息（跳过 system prompt）
            for msg in session["messages"][1:]:
                if msg["role"] == "user":
                    chat_view.append_user_message(msg["content"])
                elif msg["role"] == "assistant":
                    chat_view.append_assistant_message_start()
                    chat_view.append_assistant_chunk(msg["content"])
                    chat_view.finalize_assistant_message()

            # 更新状态栏
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.update_session(
                session_id, session["title"], session["total_tokens"]
            )
            status_bar.set_status(f"Loaded session: {session['title']}")

        except Exception as e:
            chat_view = self.query_one("#chat_view", ChatView)
            chat_view.append_error_message(f"Failed to load session: {e}")

    @on(SessionSelected)
    async def handle_session_selected(self, message: SessionSelected):
        """处理会话选中事件"""
        await self._load_session(message.session_id)

    @on(MessageSubmitted)
    async def handle_message_submitted(self, message: MessageSubmitted):
        """处理用户提交的消息"""
        if self.is_generating:
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.set_status("Please wait for the current response to complete")
            return

        user_message = message.content

        # 显示用户消息
        chat_view = self.query_one("#chat_view", ChatView)
        chat_view.append_user_message(user_message)

        # 保存用户消息
        user_tokens = count_tokens(user_message)
        self.session_manager.save_message(
            self.current_session_id, "user", user_message, update_title=True
        )

        # 更新状态
        self.is_generating = True
        status_bar = self.query_one("#status_bar", StatusBar)
        status_bar.set_status("Generating...")

        # 开始接收助手回复
        chat_view.append_assistant_message_start()

        try:
            # 获取上下文消息（已包含刚才保存的用户消息）
            session = self.session_manager.load_session(self.current_session_id)
            context_messages = await self.context_manager.get_context_messages(
                session, user_tokens
            )

            # 流式请求 LLM
            assistant_response = ""

            async def on_chunk(chunk: str):
                if not self.is_generating:
                    # 用户中断
                    return
                chat_view.append_assistant_chunk(chunk)
                nonlocal assistant_response
                assistant_response += chunk

            full_response = await self.llm_client.chat_stream(
                context_messages, on_chunk
            )

            # 完成助手消息
            chat_view.finalize_assistant_message()

            # 保存助手回复
            if self.is_generating:  # 如果没有被中断
                self.session_manager.save_message(
                    self.current_session_id, "assistant", full_response
                )

                # 更新状态栏
                session = self.session_manager.load_session(self.current_session_id)
                status_bar.update_session(
                    self.current_session_id,
                    session["title"],
                    session["total_tokens"],
                )
                status_bar.set_status("Ready")
            else:
                status_bar.set_status("Cancelled")

        except Exception as e:
            # 错误处理
            chat_view.append_error_message(str(e))
            status_bar.set_status("Error")

        finally:
            self.is_generating = False


def run():
    """运行应用"""
    app = ChatbotApp()
    app.run()
