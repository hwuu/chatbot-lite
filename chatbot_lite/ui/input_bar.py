"""输入框组件"""

from typing import List

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
    - Ctrl+J 发送消息
    - Ctrl+Up/Down 浏览历史输入
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
        self._input_history: List[str] = []  # 历史输入列表
        self._history_index: int = -1  # 当前浏览位置（-1 表示在草稿）
        self._current_draft: str = ""  # 当前正在输入的草稿

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
        # 处理历史导航快捷键
        # 在 Textual 中，Ctrl+Up 的 key 可能是 "ctrl+up" 或需要检查 character
        if event.key == "ctrl+up" or (event.key == "up" and "ctrl" in str(event.key).lower()):
            self.action_history_prev()
            event.prevent_default()
            event.stop()
            return

        if event.key == "ctrl+down" or (event.key == "down" and "ctrl" in str(event.key).lower()):
            self.action_history_next()
            event.prevent_default()
            event.stop()
            return

        # 按键后立即更新高度
        self._update_height()

        # 如果用户输入了内容（不是导航键），重置历史浏览状态
        if self._history_index != -1:
            self._history_index = -1

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

        # 将内容加入历史
        self._input_history.append(content)
        # 重置历史浏览状态
        self._history_index = -1
        self._current_draft = ""

        # 发送消息事件
        self.post_message(MessageSubmitted(content))

        # 清空输入框
        self.clear()

        # 重置高度
        self.styles.height = 5
        self._last_height = 5

    def action_history_prev(self):
        """向前浏览历史（Ctrl+Up）"""
        if not self._input_history:
            return

        # 如果当前在草稿状态，保存草稿
        if self._history_index == -1:
            self._current_draft = self.text

        # 计算新的索引位置
        if self._history_index == -1:
            # 从草稿状态进入历史，显示最后一条
            self._history_index = len(self._input_history) - 1
        elif self._history_index > 0:
            # 继续向前
            self._history_index -= 1

        # 更新输入框内容
        self.text = self._input_history[self._history_index]
        # 将光标移到末尾
        self.move_cursor_relative(rows=999, columns=999)

    def action_history_next(self):
        """向后浏览历史（Ctrl+Down）"""
        if self._history_index == -1:
            # 已经在草稿状态，无需操作
            return

        # 向后移动
        self._history_index += 1

        if self._history_index >= len(self._input_history):
            # 回到草稿状态
            self._history_index = -1
            self.text = self._current_draft
        else:
            # 显示历史记录
            self.text = self._input_history[self._history_index]

        # 将光标移到末尾
        self.move_cursor_relative(rows=999, columns=999)

    def clear_history(self):
        """清空历史记录（切换会话时调用）"""
        self._input_history.clear()
        self._history_index = -1
        self._current_draft = ""

    def load_history(self, messages: list):
        """
        从会话消息中加载用户输入历史

        Args:
            messages: 会话消息列表，每个消息包含 role 和 content
        """
        # 清空当前历史
        self._input_history.clear()
        self._history_index = -1
        self._current_draft = ""

        # 提取所有 user 消息
        user_messages = [msg["content"] for msg in messages if msg.get("role") == "user"]

        # 加载到历史中
        self._input_history.extend(user_messages)

    def get_draft_state(self) -> dict:
        """
        获取当前草稿状态

        Returns:
            包含 draft 和 history_index 的字典
        """
        return {
            "draft": self.text,
            "history_index": self._history_index
        }

    def set_draft_state(self, state: dict):
        """
        设置草稿状态

        Args:
            state: 包含 draft 和 history_index 的字典
        """
        if state:
            draft = state.get("draft", "")
            history_index = state.get("history_index", -1)

            self.text = draft
            self._history_index = history_index
        else:
            self.text = ""
            self._history_index = -1

    def set_placeholder(self, text: str):
        """
        设置占位符文本

        Args:
            text: 占位符内容
        """
        # Textual TextArea 不支持 placeholder，这里可以通过其他方式实现
        # 暂时留空，未来可以优化
        pass
