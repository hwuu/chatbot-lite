"""对话显示区组件"""

import math

from rich.markdown import Markdown
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import RichLog, Static


class ChatView(VerticalScroll):
    """对话显示区域，支持 Markdown 渲染和流式输出"""

    can_focus = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_assistant_message = ""
        self._last_assistant_message = ""
        self._streaming_widget = None  # 流式输出的临时 widget
        self._assistant_label = None  # 助手标签引用（用于动画）
        self._blink_timer = None  # 闪动定时器
        self._blink_phase = 0.0  # 闪动相位（0-1）

    def on_mount(self):
        """挂载时初始化"""
        pass

    def append_user_message(self, content: str):
        """
        添加用户消息

        Args:
            content: 用户消息内容
        """
        # 添加用户消息标签
        label = Static(Text("● You", style="bold cyan"))
        self.mount(label)
        # 添加消息内容（缩进两个空格）
        content_widget = Static(Markdown(content), classes="message-content")
        self.mount(content_widget)
        # 自动滚动到底部
        self.scroll_end(animate=False)

    def append_assistant_message_start(self):
        """开始接收助手消息（流式）"""
        # 添加助手标签
        self._assistant_label = Static(Text("● Assistant", style="bold green"), classes="assistant-label")
        self.mount(self._assistant_label)
        # 创建流式输出的临时 widget（缩进两个空格）
        self._streaming_widget = Static("", classes="message-content")
        self.mount(self._streaming_widget)
        self._current_assistant_message = ""

        # 启动闪动动画
        self._start_blink_animation()

    def append_assistant_chunk(self, chunk: str):
        """
        追加助手消息片段（流式输出）

        Args:
            chunk: 文本片段
        """
        self._current_assistant_message += chunk
        # 实时更新流式 widget 的内容
        if self._streaming_widget:
            self._streaming_widget.update(self._current_assistant_message)
        # 自动滚动到底部
        self.scroll_end(animate=False)

    def finalize_assistant_message(self):
        """
        完成助手消息（完整渲染 Markdown）
        """
        # 停止闪动动画
        self._stop_blink_animation()

        # 重置助手标签为正常状态
        if self._assistant_label:
            self._assistant_label.update(Text("● Assistant", style="bold green"))
            self._assistant_label = None

        # 移除流式 widget
        if self._streaming_widget:
            self._streaming_widget.remove()
            self._streaming_widget = None

        # 添加最终的 Markdown 渲染版本（缩进两个空格）
        if self._current_assistant_message:
            content_widget = Static(Markdown(self._current_assistant_message), classes="message-content")
            self.mount(content_widget)

        # 添加分割线
        separator = Static(Text("─" * 80, style="dim"))
        self.mount(separator)

        # 保存最后一条助手消息
        self._last_assistant_message = self._current_assistant_message
        # 清空当前缓冲
        self._current_assistant_message = ""

        # 自动滚动到底部
        self.scroll_end(animate=False)

    def get_last_assistant_message(self) -> str:
        """获取最后一条助手消息"""
        return self._last_assistant_message

    def append_system_message(self, content: str):
        """
        添加系统消息

        Args:
            content: 系统消息内容
        """
        widget = Static(Text(content, style="italic dim"))
        self.mount(widget)

    def append_error_message(self, error: str):
        """
        添加错误消息

        Args:
            error: 错误信息
        """
        widget = Static(Text(f"Error: {error}", style="bold red"))
        self.mount(widget)

    def clear_chat(self):
        """清空聊天记录"""
        # 停止闪动动画
        self._stop_blink_animation()
        # 移除所有子 widget
        for child in list(self.children):
            child.remove()

    def _start_blink_animation(self):
        """启动闪动动画"""
        self._blink_phase = 0.0
        # 每 0.05 秒更新一次（每秒 20 帧）
        self._blink_timer = self.set_interval(0.05, self._update_blink)

    def _stop_blink_animation(self):
        """停止闪动动画"""
        if self._blink_timer:
            self._blink_timer.stop()
            self._blink_timer = None
        self._blink_phase = 0.0

    def _update_blink(self):
        """更新闪动效果"""
        if not self._assistant_label:
            self._stop_blink_animation()
            return

        # 更新相位（0.05秒 * 20帧 = 1秒一个周期）
        self._blink_phase = (self._blink_phase + 0.05) % 1.0

        # 计算透明度（通过 cos 函数实现平滑过渡）
        # 0.5 秒内从 1.0 降到 0.5，再升到 1.0
        opacity = 0.75 + 0.25 * math.cos(self._blink_phase * 2 * math.pi)

        # 通过调整绿色的亮度来模拟透明度
        # bold green 对应 RGB(0, 255, 0)
        # 将亮度乘以 opacity
        brightness = int(255 * opacity)
        color = f"rgb({0},{brightness},{0})"

        # 更新标签
        self._assistant_label.update(Text("● Assistant", style=f"bold {color}"))
