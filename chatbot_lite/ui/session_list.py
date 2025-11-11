"""会话列表侧边栏组件"""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Label, ListItem, ListView, Static


class SessionSelected(Message):
    """会话被选中的事件"""

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id


class SessionList(Container):
    """
    会话列表侧边栏

    显示所有历史会话，支持：
    - 点击切换会话
    - 显示会话标题和时间
    - 可折叠/展开
    """

    DEFAULT_CSS = """
    SessionList {
        width: 50;
        height: 100%;
        border: solid $primary;
        padding: 1;
        margin: 1;
    }

    SessionList.hidden {
        display: none;
    }

    SessionList #session_title {
        text-align: center;
        text-style: bold;
        background: $boost;
        margin-bottom: 1;
    }

    SessionList ListView {
        height: 1fr;
        border: solid $accent;
    }

    SessionList #new_session_btn {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs, classes="hidden")  # 默认隐藏
        self.sessions = []

    def compose(self) -> ComposeResult:
        """组合组件"""
        yield Label("Sessions", id="session_title")
        yield ListView(id="session_listview")
        yield Button("New Session (Ctrl+N)", id="new_session_btn", variant="primary")

    def toggle_visibility(self):
        """切换显示/隐藏"""
        self.toggle_class("hidden")

    def update_sessions(self, sessions: list):
        """
        更新会话列表

        Args:
            sessions: 会话列表 [{"session_id": ..., "title": ..., "updated_at": ...}]
        """
        self.sessions = sessions
        listview = self.query_one("#session_listview", ListView)
        listview.clear()

        for session in sessions:
            # 格式化标题
            title = session["title"]
            if len(title) > 25:
                title = title[:25] + "..."

            # 格式化时间
            updated_at = session["updated_at"][:10]  # 只取日期部分

            # 创建列表项
            item_text = f"{title}\n{updated_at}"
            list_item = ListItem(Label(item_text))
            list_item.session_id = session["session_id"]  # 附加 session_id
            listview.append(list_item)

    @on(ListView.Selected)
    def on_session_selected(self, event: ListView.Selected):
        """处理会话选中事件"""
        if hasattr(event.item, "session_id"):
            self.post_message(SessionSelected(event.item.session_id))

    @on(Button.Pressed, "#new_session_btn")
    def on_new_session_pressed(self, event: Button.Pressed):
        """处理新建会话按钮"""
        # 触发应用的新建会话动作
        self.app.action_new_session()
