"""输入框组件"""

from textual import events, on
from textual.binding import Binding
from textual.message import Message
from textual.widgets import TextArea


class MessageSubmitted(Message):
    """用户提交消息的事件"""

    def __init__(self, content: str):
        super().__init__()
        self.content = content


class InputBar(TextArea):
    """
    多行输入框

    支持：
    - 多行输入
    - Enter 换行
    - Ctrl+Enter 发送消息
    - 高度自适应（5-25行）
    """

    BINDINGS = [
        Binding("ctrl+j", "submit", "Send", show=True, priority=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            soft_wrap=True,
            show_line_numbers=False,
        )
        self._last_height = 5  # 记录上次的高度

    def on_mount(self):
        """挂载时设置初始高度"""
        super().on_mount()
        self.styles.height = 5  # 初始高度
        self._last_height = 5

    def _update_height(self) -> None:
        """更新输入框高度"""
        # 计算行数
        line_count = len(self.text.split("\n")) if self.text else 1

        # 动态调整高度：行数 + 4（2行padding + 2行额外），最小5行，最大25行
        new_height = max(5, min(line_count + 4, 25))

        # 只在高度真正需要变化时才更新
        if new_height != self._last_height:
            self.styles.height = new_height
            self._last_height = new_height

    def on_key(self, event: events.Key) -> None:
        """按键事件处理"""
        # 按键后立即更新高度
        self._update_height()

    @on(TextArea.Changed)
    def on_textarea_changed(self) -> None:
        """文本变化事件处理"""
        self._update_height()

    def action_submit(self):
        """提交消息的 action"""
        self.run_worker(self.submit_message())

    async def submit_message(self):
        """提交消息"""
        content = self.text.strip()
        if not content:
            return

        # 发送消息事件
        self.post_message(MessageSubmitted(content))

        # 清空输入框
        self.clear()

        # 重置高度
        self.styles.height = 5
        self._last_height = 5

    def set_placeholder(self, text: str):
        """
        设置占位符文本

        Args:
            text: 占位符内容
        """
        # Textual TextArea 不支持 placeholder，这里可以通过其他方式实现
        # 暂时留空，未来可以优化
        pass
