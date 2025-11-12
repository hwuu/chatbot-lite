"""LLM 客户端模块

负责与本地 LLM API 进行流式通信。
"""

import re
from typing import Callable, Dict, List, Awaitable

from openai import AsyncOpenAI

from chatbot_lite.config import LLMConfig


class ThinkTagFilter:
    """过滤 <think>...</think> 标签的状态机"""

    def __init__(self):
        self.buffer = ""
        self.in_think = False
        self.output_buffer = ""

    def process_chunk(self, chunk: str) -> str:
        """
        处理流式输入的文本块，过滤掉 <think>...</think> 标签

        Args:
            chunk: 输入的文本块

        Returns:
            过滤后可以输出的文本
        """
        self.buffer += chunk
        output = ""

        while self.buffer:
            if not self.in_think:
                # 查找 <think> 标签
                think_start = self.buffer.find("<think>")
                if think_start != -1:
                    # 输出标签之前的内容
                    output += self.buffer[:think_start]
                    self.buffer = self.buffer[think_start + 7:]  # 跳过 <think>
                    self.in_think = True
                else:
                    # 检查 buffer 末尾是否可能是不完整的标签
                    # 保留最后 6 个字符以防是 "<think" 的一部分
                    if len(self.buffer) > 6:
                        safe_len = len(self.buffer) - 6
                        output += self.buffer[:safe_len]
                        self.buffer = self.buffer[safe_len:]
                    break
            else:
                # 在 think 标签内，查找 </think> 标签
                think_end = self.buffer.find("</think>")
                if think_end != -1:
                    # 丢弃标签内的内容，跳过 </think>
                    self.buffer = self.buffer[think_end + 8:]
                    self.in_think = False
                else:
                    # 保留最后 7 个字符以防是不完整的 "</think" 的一部分
                    if len(self.buffer) > 8:
                        # 丢弃 think 标签内的内容
                        self.buffer = self.buffer[-(8):]
                    break

        return output

    def finalize(self) -> str:
        """
        处理结束，输出剩余的 buffer

        Returns:
            剩余的可输出文本
        """
        if not self.in_think:
            output = self.buffer
            self.buffer = ""
            return output
        return ""


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
            完整的回复文本（已移除 <think>...</think> 标签）

        Raises:
            Exception: API 调用错误
        """
        full_response = ""
        think_filter = ThinkTagFilter()

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

                    # 通过过滤器处理，移除 <think>...</think> 标签
                    filtered_content = think_filter.process_chunk(content)

                    # 如果是第一个有效输出，去除前导空格
                    if filtered_content and not full_response:
                        filtered_content = filtered_content.lstrip()

                    if filtered_content:
                        full_response += filtered_content
                        await on_chunk(filtered_content)

            # 处理结束，输出剩余 buffer
            remaining = think_filter.finalize()
            if remaining:
                if not full_response:
                    remaining = remaining.lstrip()
                full_response += remaining
                await on_chunk(remaining)

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

    async def generate_title(self, user_message: str) -> str:
        """
        根据用户的第一条消息生成会话标题

        Args:
            user_message: 用户的第一条消息

        Returns:
            生成的标题（10个字以内）

        Raises:
            Exception: API 调用错误
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一个标题生成助手。根据用户的提问，生成一个简洁的主题标题，要求：1）20个字以内 2）尽量简短 3）只输出标题，不要其他内容"
                },
                {
                    "role": "user",
                    "content": f"请为以下提问生成一个简短的标题：\n\n{user_message}"
                }
            ]

            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=0.7,
                max_tokens=50,
                stream=False,
            )

            title = response.choices[0].message.content.strip()
            # 移除可能的引号
            title = title.strip('"').strip("'")
            # 限制长度
            if len(title) > 30:
                title = title[:30]

            return title

        except Exception as e:
            # 如果生成失败，返回截取的用户消息
            return user_message[:30] if len(user_message) > 30 else user_message
