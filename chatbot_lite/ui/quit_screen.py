"""退出确认对话框组件"""

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class QuitScreen(ModalScreen[bool]):
    """退出确认对话框"""

    DEFAULT_CSS = """
    QuitScreen {
        align: center middle;
    }

    #quit_dialog {
        width: 60;
        height: 14;
        border: thick $error;
        background: $surface;
        padding: 1;
    }

    #quit_title {
        text-align: center;
        text-style: bold;
        background: $boost;
        margin-bottom: 1;
    }

    #quit_message {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
        padding: 1;
    }

    #quit_hint {
        text-align: center;
        width: 100%;
        margin-bottom: 2;
        color: $text-muted;
    }

    #quit_buttons {
        height: auto;
        width: 100%;
        align-horizontal: center;
    }

    #quit_buttons Button {
        margin: 0 2;
        min-width: 18;
        height: auto;
        min-height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        """组合组件"""
        with Container(id="quit_dialog"):
            yield Label("确认退出", id="quit_title")
            yield Label("确定要退出 Chatbot-Lite 吗？", id="quit_message")
            #yield Label("(按 Y 退出 / 按 N 或 Esc 取消)", id="quit_hint")
            with Horizontal(id="quit_buttons"):
                yield Button("是 (Y)", id="yes_btn", variant="error")
                yield Button("否 (N)", id="no_btn", variant="primary")

    def on_mount(self):
        """挂载时聚焦到"否"按钮（默认选项）"""
        no_btn = self.query_one("#no_btn", Button)
        no_btn.focus()

    @on(Button.Pressed, "#yes_btn")
    def on_yes_pressed(self, event: Button.Pressed):
        """用户确认退出"""
        self.dismiss(True)

    @on(Button.Pressed, "#no_btn")
    def on_no_pressed(self, event: Button.Pressed):
        """用户取消退出"""
        self.dismiss(False)

    def on_key(self, event):
        """处理按键"""
        if event.key == "escape":
            # Esc 相当于选择"否"
            event.prevent_default()
            event.stop()
            self.dismiss(False)
        elif event.key == "y":
            # Y 键确认退出
            event.prevent_default()
            event.stop()
            self.dismiss(True)
        elif event.key == "n":
            # N 键取消退出
            event.prevent_default()
            event.stop()
            self.dismiss(False)
