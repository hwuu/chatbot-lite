"""搜索对话框组件"""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView


class SearchResultSelected(Message):
    """搜索结果被选中的事件"""

    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id


class SearchScreen(ModalScreen):
    """搜索对话框模态窗口"""

    DEFAULT_CSS = """
    SearchScreen {
        align: center middle;
    }

    #search_dialog {
        width: 60;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #search_title {
        text-align: center;
        text-style: bold;
        background: $boost;
        margin-bottom: 1;
    }

    #search_input {
        margin-bottom: 1;
    }

    #search_results {
        height: 1fr;
        border: solid $accent;
        margin-bottom: 1;
    }

    #search_buttons {
        height: 3;
        align: center middle;
    }

    #search_buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, session_manager, **kwargs):
        super().__init__(**kwargs)
        self.session_manager = session_manager
        self.search_results = []

    def compose(self) -> ComposeResult:
        """组合组件"""
        with Container(id="search_dialog"):
            yield Label("Search Sessions", id="search_title")
            yield Input(placeholder="Enter keyword...", id="search_input")
            yield ListView(id="search_results")
            with Container(id="search_buttons"):
                yield Button("Close (Esc)", id="close_btn", variant="default")

    def on_mount(self):
        """挂载时聚焦到输入框"""
        input_widget = self.query_one("#search_input", Input)
        input_widget.focus()

    @on(Input.Changed, "#search_input")
    def on_search_input_changed(self, event: Input.Changed):
        """处理搜索输入变化"""
        keyword = event.value.strip()

        if not keyword:
            # 清空结果
            listview = self.query_one("#search_results", ListView)
            listview.clear()
            return

        # 执行搜索
        self.search_results = self.session_manager.search_sessions(keyword)

        # 更新结果列表
        listview = self.query_one("#search_results", ListView)
        listview.clear()

        if not self.search_results:
            listview.append(ListItem(Label("No results found")))
        else:
            for result in self.search_results:
                title = result["title"]
                if len(title) > 40:
                    title = title[:40] + "..."

                match_type = result.get("match_type", "")
                if match_type == "title":
                    label_text = f"[Title] {title}"
                else:
                    preview = result.get("match_preview", "")
                    if len(preview) > 50:
                        preview = preview[:50] + "..."
                    label_text = f"{title}\n  {preview}"

                list_item = ListItem(Label(label_text))
                list_item.session_id = result["session_id"]
                listview.append(list_item)

    @on(ListView.Selected, "#search_results")
    def on_result_selected(self, event: ListView.Selected):
        """处理结果选中"""
        if hasattr(event.item, "session_id"):
            # 发送选中事件并关闭对话框
            self.dismiss(event.item.session_id)

    @on(Button.Pressed, "#close_btn")
    def on_close_pressed(self, event: Button.Pressed):
        """关闭对话框"""
        self.dismiss(None)

    def on_key(self, event):
        """处理按键"""
        if event.key == "escape":
            self.dismiss(None)
