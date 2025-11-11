"""状态栏组件"""

from textual.widgets import Label


class StatusBar(Label):
    """
    状态栏，显示：
    - 当前会话信息
    - Token 计数
    - 状态提示
    """

    def __init__(self, **kwargs):
        super().__init__("Ready", **kwargs)
        self.current_session = None
        self.total_tokens = 0
        self.status_message = "Ready"

    def update_session(self, session_id: str, title: str, tokens: int):
        """
        更新会话信息

        Args:
            session_id: 会话 ID
            title: 会话标题
            tokens: 总 token 数
        """
        self.current_session = session_id
        self.total_tokens = tokens
        self._refresh_display()

    def update_tokens(self, tokens: int):
        """
        更新 token 计数

        Args:
            tokens: 当前总 token 数
        """
        self.total_tokens = tokens
        self._refresh_display()

    def set_status(self, message: str):
        """
        设置状态消息

        Args:
            message: 状态消息
        """
        self.status_message = message
        self._refresh_display()

    def _refresh_display(self):
        """刷新显示"""
        parts = []

        # 状态消息
        if self.status_message:
            parts.append(self.status_message)

        # Token 计数
        if self.total_tokens > 0:
            parts.append(f"Tokens: {self.total_tokens}")

        # 会话信息
        if self.current_session:
            parts.append(f"Session: {self.current_session[:8]}...")

        self.update(" | ".join(parts))
