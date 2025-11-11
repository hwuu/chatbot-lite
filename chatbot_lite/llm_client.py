"""LLM 客户端模块

负责与本地 LLM API 进行流式通信。
"""

from typing import Callable, Dict, List, Awaitable

from openai import AsyncOpenAI

from chatbot_lite.config import LLMConfig


class LLMClient:
    """LLM API 客户端"""

    def __init__(self, config: LLMConfig):
        """
        初始化 LLM 客户端

        Args:
            config: LLM 配置对象
        """
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
        )

    async def close(self):
        """关闭客户端连接"""
        await self.client.close()

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        on_chunk: Callable[[str], Awaitable[None]],
    ) -> str:
        """
        流式对话

        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}, ...]
            on_chunk: 回调函数，接收每个生成的文本片段

        Returns:
            完整的回复文本

        Raises:
            Exception: API 调用错误
        """
        full_response = ""

        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    await on_chunk(content)

        except Exception as e:
            raise Exception(f"LLM API 调用失败: {e}")

        return full_response

    async def chat(
        self,
        messages: List[Dict[str, str]],
    ) -> str:
        """
        非流式对话（用于压缩等场景）

        Args:
            messages: 对话历史

        Returns:
            完整的回复文本

        Raises:
            Exception: API 调用错误
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=False,
            )

            return response.choices[0].message.content

        except Exception as e:
            raise Exception(f"LLM API 调用失败: {e}")
