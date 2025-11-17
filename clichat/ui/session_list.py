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
        width: 44;
        height: 100%;
        border: solid $primary;
        padding: 1;
        margin: 1;
    }

    SessionList.hidden {
        display: none;
    }

    SessionList #session_logo {
        color: $primary;
        margin-bottom: 1;
        width: auto;
        align-horizontal: center;
    }

    SessionList #session_title {
        text-align: center;
        text-style: bold;
        background: $boost;
        margin-bottom: 1;
    }

    SessionList ListView {
        height: 1fr;
    }

    SessionList ListView Label {
        color: $text;
    }

    SessionList #new_session_btn {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)  # 默认显示
        self.sessions = []

    def compose(self) -> ComposeResult:
        """组合组件"""
        # ASCII art logo
        logo = r"""
▄█████ ▄▄    ▄▄ ▄█████ ▄▄ ▄▄  ▄▄▄ ▄▄▄▄▄▄
██     ██    ██ ██     ██▄██ ██▀██  ██
▀█████ ██▄▄▄ ██ ▀█████ ██ ██ ██▀██  ██
"""
        yield Static(logo.strip(), id="session_logo")
        yield ListView(id="session_listview")

    def toggle_visibility(self):
        """切换显示/隐藏"""
        self.toggle_class("hidden")

    def update_sessions(self, sessions: list, current_session_id: str = None):
        """
        更新会话列表

        Args:
            sessions: 会话列表 [{"session_id": ..., "title": ..., "updated_at": ...}]
            current_session_id: 当前选中的会话 ID
        """
        self.sessions = sessions
        listview = self.query_one("#session_listview", ListView)
        listview.clear()

        selected_index = None
        for index, session in enumerate(sessions):
            # 格式化标题
            title = session["title"]
            if len(title) > 25:
                title = title[:25] + "..."

            # 格式化时间为 YYYY-MM-DD HH:MM:SS
            # updated_at 格式: 2025-11-13T15:30:33.123456
            updated_at = session["updated_at"][:19].replace("T", " ")  # YYYY-MM-DD HH:MM:SS

            # 创建列表项，在标题前加标记符号，日期使用深灰色
            item_text = f"▸ {title}\n  [#666666]{updated_at}[/#666666]"
            list_item = ListItem(Label(item_text, markup=True))
            list_item.session_id = session["session_id"]  # 附加 session_id
            listview.append(list_item)

            # 记录当前会话的索引
            if current_session_id and session["session_id"] == current_session_id:
                selected_index = index

        # 所有项添加完成后，设置选中状态
        if selected_index is not None and len(listview.children) > 0:
            # 使用 set_timer 确保在下一个事件循环中执行
            self.set_timer(0.01, lambda: self._select_index(selected_index))

    def _select_index(self, index: int):
        """延迟设置选中索引"""
        try:
            listview = self.query_one("#session_listview", ListView)
            if index < len(listview.children):
                listview.index = index
        except Exception:
            pass

    @on(ListView.Selected)
    def on_session_selected(self, event: ListView.Selected):
        """处理会话选中事件"""
        if hasattr(event.item, "session_id"):
            self.post_message(SessionSelected(event.item.session_id))

    #@on(Button.Pressed, "#new_session_btn")
    #def on_new_session_pressed(self, event: Button.Pressed):
    #    """处理新建会话按钮"""
    #    # 触发应用的新建会话动作
    #    self.app.action_new_session()
