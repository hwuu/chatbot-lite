"""对话显示区组件"""

import math

from rich.text import Text
from textual import on
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Markdown, Static


class CopyButton(Button):
    """带有消息内容的复制按钮"""

    def __init__(self, message_content: str, **kwargs):
        super().__init__("复制到剪贴板", **kwargs)
        self.message_content = message_content


class ChatView(VerticalScroll):
    """对话显示区域，支持 Markdown 渲染和流式输出"""

    can_focus = False

    def __init__(self, code_theme: str = "monokai", **kwargs):
        super().__init__(**kwargs)
        self._current_assistant_message = ""
        self._last_assistant_message = ""
        self._streaming_widget = None  # 流式输出的临时 widget
        self._assistant_label = None  # 助手标签引用（用于动画）
        self._blink_timer = None  # 闪动定时器
        self._blink_phase = 0.0  # 闪动相位（0-1）
        self._code_theme = code_theme  # Markdown 代码块主题

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
        label = Static(Text("\n● You\n", style="bold cyan"))
        self.mount(label)
        # 添加消息内容（可选择，缩进两个空格，使用配置的代码主题，左对齐）
        content_widget = Static(
            Text(content),
            #Markdown(content, code_theme=self._code_theme, justify="left"),
            classes="message-content"
        )
        self.mount(content_widget)
        # 自动滚动到底部
        self.scroll_end(animate=False)

    def append_assistant_message_start(self):
        """开始接收助手消息（流式）"""
        # 添加助手标签
        self._assistant_label = Static(Text("\n● Assistant\n", style="bold green"), classes="assistant-label")
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

        # 重置助手标签为正常状态（完全不透明）
        if self._assistant_label:
            self._assistant_label.update(Text("\n● Assistant\n", style="bold rgb(0,255,0)"))
            self._assistant_label = None

        # 移除流式 widget
        if self._streaming_widget:
            self._streaming_widget.remove()
            self._streaming_widget = None

        # 添加最终的 Markdown 渲染版本（可选择，缩进两个空格）
        if self._current_assistant_message:
            content_widget = Markdown(
                self._current_assistant_message,
                classes="message-content"
            )
            self.mount(content_widget)

            # 添加复制按钮
            copy_button = CopyButton(
                self._current_assistant_message,
                variant="default",
                classes="copy-button"
            )
            button_container = Horizontal(copy_button, classes="copy-button-container")
            self.mount(button_container)

        ## 添加分割线
        #separator = Static(Text("─" * 80, style="dim"))
        #self.mount(separator)

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

    @on(Button.Pressed, ".copy-button")
    def on_copy_button_pressed(self, event: Button.Pressed):
        """处理复制按钮点击事件"""
        if isinstance(event.button, CopyButton):
            success = False
            try:
                # 尝试使用 app 的 clipboard 功能
                self.app.copy_to_clipboard(event.button.message_content)
                success = True
            except Exception:
                # 如果失败，尝试使用 pyperclip
                try:
                    import pyperclip
                    pyperclip.copy(event.button.message_content)
                    success = True
                except Exception:
                    pass

            # 如果复制成功，显示通知
            if success:
                char_count = len(event.button.message_content)
                self.app.notify(f"{char_count} 字符已复制到剪贴板", timeout=5.0)

            # 复制完成后，将焦点返回到输入框
            try:
                input_bar = self.app.query_one("#input_bar")
                input_bar.focus()
            except Exception:
                pass

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
        # 每 0.1 秒更新一次，2 秒一个周期
        self._blink_timer = self.set_interval(0.1, self._update_blink)

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

        # 更新相位（0.1秒 * 20次 = 2秒一个周期）
        self._blink_phase = (self._blink_phase + 0.05) % 1.0

        # 计算透明度（通过 cos 函数实现平滑过渡）
        # 范围：0.3 到 1.0
        opacity = 0.65 + 0.35 * math.cos(self._blink_phase * 2 * math.pi)

        # 通过调整绿色的亮度来模拟透明度
        # bold green 对应 RGB(0, 255, 0)
        # 将亮度乘以 opacity
        brightness = int(255 * opacity)
        color = f"rgb({0},{brightness},{0})"

        # 更新标签
        self._assistant_label.update(Text("\n● Assistant\n", style=f"bold {color}"))
