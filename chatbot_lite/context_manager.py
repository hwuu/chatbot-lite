"""上下文管理模块

实现懒惰压缩策略，智能管理对话上下文。
"""

from typing import Dict, List, Optional

from chatbot_lite.config import AppConfig
from chatbot_lite.llm_client import LLMClient


class ContextManager:
    """上下文管理器

    使用懒惰压缩策略：
    1. 未超过阈值时：返回全部消息
    2. 超过阈值时：
       - 保留最近 N 条完整消息
       - 将更早的消息压缩成摘要（一次性调用 LLM）
       - 组合：[system] + [摘要] + [最近消息]
    """

    def __init__(self, config: AppConfig, llm_client: LLMClient):
        """
        初始化上下文管理器

        Args:
            config: 应用配置
            llm_client: LLM 客户端（用于压缩）
        """
        self.config = config
        self.llm_client = llm_client
        self._compressed_summary: Optional[str] = None  # 缓存压缩后的摘要
        self._recent_message_count = 10  # 保留最近 N 条消息

    async def get_context_messages(
        self, session: Dict, current_input_tokens: int
    ) -> List[Dict[str, str]]:
        """
        获取用于发送给 LLM 的上下文消息列表

        Args:
            session: 会话数据（包含 messages, total_tokens 等）
            current_input_tokens: 当前用户输入的 token 数

        Returns:
            处理后的消息列表，可能包含压缩的历史摘要
        """
        max_tokens = self.llm_client.config.max_tokens
        threshold = int(max_tokens * self.config.compress_threshold)

        messages = session["messages"]
        total_tokens = session["total_tokens"] + current_input_tokens

        # 情况 1：未超过阈值，返回全部消息
        if total_tokens < threshold:
            return messages

        # 情况 2：需要压缩
        system_msg = messages[0]  # system prompt（始终保留）
        history = messages[1:]  # 用户对话历史

        # 如果历史消息少于保留数量，直接返回
        if len(history) <= self._recent_message_count:
            return messages

        # 分割历史：旧消息 + 最近消息
        recent_msgs = history[-self._recent_message_count :]
        old_msgs = history[: -self._recent_message_count]

        # 如果还没有压缩过，执行压缩
        if self._compressed_summary is None and old_msgs:
            self._compressed_summary = await self._compress_messages(old_msgs)

        # 组合最终上下文
        result = [system_msg]

        # 添加压缩摘要（如果有）
        if self._compressed_summary:
            result.append(
                {
                    "role": "system",
                    "content": f"[Previous conversation summary]\n{self._compressed_summary}",
                }
            )

        # 添加最近的消息
        result.extend(recent_msgs)

        return result

    async def _compress_messages(self, messages: List[Dict]) -> str:
        """
        调用 LLM 压缩历史消息为摘要

        Args:
            messages: 需要压缩的消息列表

        Returns:
            压缩后的摘要文本
        """
        # 构造对话文本
        conversation_text = "\n\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in messages]
        )

        # 构造压缩提示词
        compress_prompt = [
            {"role": "system", "content": "You are a conversation summarizer."},
            {
                "role": "user",
                "content": f"""Please summarize the following conversation into {self.config.compress_summary_tokens} tokens or less.
Focus on key information, decisions, and context that would be useful for continuing the conversation.

Conversation:
{conversation_text}

Summary:""",
            },
        ]

        # 调用 LLM 生成摘要（使用非流式接口）
        try:
            summary = await self.llm_client.chat(compress_prompt)
            return summary.strip()
        except Exception as e:
            # 如果压缩失败，返回简单的截断摘要
            # 这样即使 LLM 不可用，系统仍可继续运行
            fallback_summary = conversation_text[: self.config.compress_summary_tokens * 4]
            return f"[Compression failed, showing truncated history]\n{fallback_summary}"

    def reset_compression(self):
        """重置压缩缓存（新会话时调用）"""
        self._compressed_summary = None

    def get_compression_status(self) -> Dict:
        """
        获取压缩状态信息（用于调试和监控）

        Returns:
            包含压缩状态的字典
        """
        return {
            "has_compressed": self._compressed_summary is not None,
            "summary_length": (
                len(self._compressed_summary) if self._compressed_summary else 0
            ),
            "recent_message_count": self._recent_message_count,
            "threshold": self.config.compress_threshold,
        }
