"""LLM 客户端模块

负责与本地 LLM API 进行流式通信。
"""

import asyncio
import re
import time
from typing import Callable, Dict, List, Awaitable

import httpx
from openai import AsyncOpenAI

from clichat.config import LLMConfig
from clichat.logger import get_logger
from clichat.utils import count_tokens


class GenerationCancelled(Exception):
    """生成被用户取消的异常"""
    pass


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
        self.logger = get_logger(__name__)

        # 创建禁用代理的 HTTP 客户端
        # proxy=None: 显式设置不使用代理
        # trust_env=False: 忽略环境变量中的代理设置（HTTP_PROXY, HTTPS_PROXY 等）
        http_client = httpx.AsyncClient(
            proxy=None,  # 显式禁用代理
            trust_env=False,  # 忽略环境变量
            timeout=60.0,  # 设置超时时间
        )

        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.api_base,
            http_client=http_client,
        )
        self.logger.info(f"LLM 客户端初始化: 模型={config.model}, API地址={config.api_base}, 已禁用代理")

    async def close(self):
        """关闭客户端连接"""
        await self.client.close()

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        on_chunk: Callable[[str], Awaitable[None]],
        is_cancelled: Callable[[], bool] = None,
    ) -> str:
        """
        流式对话

        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}, ...]
            on_chunk: 回调函数，接收每个生成的文本片段
            is_cancelled: 可选的取消检查函数，返回 True 表示用户取消

        Returns:
            完整的回复文本（已移除 <think>...</think> 标签）

        Raises:
            Exception: API 调用错误
        """
        # 计算输入 token 数
        input_tokens = sum(count_tokens(msg["content"]) for msg in messages)
        self.logger.info(f"开始流式 LLM 调用: 消息数={len(messages)}, 输入tokens={input_tokens}")

        start_time = time.time()
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
                # 检查是否被用户取消
                if is_cancelled and is_cancelled():
                    self.logger.info("检测到用户取消信号，中断流式生成")
                    raise GenerationCancelled()

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

                # 让出控制权，允许事件循环处理其他事件（如键盘输入）
                await asyncio.sleep(0)

            # 处理结束，输出剩余 buffer
            remaining = think_filter.finalize()
            if remaining:
                if not full_response:
                    remaining = remaining.lstrip()
                full_response += remaining
                await on_chunk(remaining)

            # 计算输出 token 数和响应时间
            output_tokens = count_tokens(full_response)
            elapsed_time = time.time() - start_time
            self.logger.info(
                f"流式 LLM 调用成功: 输出tokens={output_tokens}, "
                f"响应时间={elapsed_time:.2f}s"
            )

        except GenerationCancelled:
            # 用户主动取消生成
            elapsed_time = time.time() - start_time
            self.logger.info(f"流式生成被用户取消, 已生成tokens={count_tokens(full_response)}, 耗时={elapsed_time:.2f}s")
            # 不抛出异常，返回已生成的内容
            return full_response

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(
                f"流式 LLM 调用失败: {e}, 耗时={elapsed_time:.2f}s",
                exc_info=True
            )
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
            完整的回复文本（已移除 <think>...</think> 标签）

        Raises:
            Exception: API 调用错误
        """
        # 计算输入 token 数
        input_tokens = sum(count_tokens(msg["content"]) for msg in messages)
        self.logger.info(f"开始非流式 LLM 调用: 消息数={len(messages)}, 输入tokens={input_tokens}")

        start_time = time.time()

        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=False,
            )

            content = response.choices[0].message.content

            # 过滤 <think>...</think> 标签
            think_filter = ThinkTagFilter()
            filtered_content = think_filter.process_chunk(content)
            filtered_content += think_filter.finalize()

            # 计算输出 token 数和响应时间
            output_tokens = count_tokens(filtered_content)
            elapsed_time = time.time() - start_time
            self.logger.info(
                f"非流式 LLM 调用成功: 输出tokens={output_tokens}, "
                f"响应时间={elapsed_time:.2f}s"
            )

            return filtered_content.strip()

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(
                f"非流式 LLM 调用失败: {e}, 耗时={elapsed_time:.2f}s",
                exc_info=True
            )
            raise Exception(f"LLM API 调用失败: {e}")

    async def generate_title(self, user_message: str) -> str:
        """
        根据用户的第一条消息生成会话标题

        Args:
            user_message: 用户的第一条消息

        Returns:
            生成的标题

        Raises:
            Exception: API 调用错误
        """
        self.logger.info("开始生成会话标题")
        start_time = time.time()

        try:
            messages = [
                {
                    "role": "system",
                    "content": "你是一个标题生成助手。根据用户的提问，生成一个简洁的主题标题，要求：" + \
                               "1）只输出标题，不要其他内容；" + \
                               "2）长度不超过 40 字符（每个英文字母、数字、半角符号占 1 个字符，每个中文字、全角符号占 2 个字符）。"
                },
                {
                    "role": "user",
                    "content": f"请为以下提问所引发的可能的对话生成一个标题：\n\n{user_message}"
                }
            ]

            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=0.7,
                max_tokens=self.config.max_tokens,
                stream=False,
            )

            title = response.choices[0].message.content

            # 过滤 <think>...</think> 标签
            think_filter = ThinkTagFilter()
            title = think_filter.process_chunk(title)
            title += think_filter.finalize()

            # 清理标题
            title = title.strip()
            # 移除可能的引号
            title = title.strip('"').strip("'")
            # 限制长度
            if len(title) > 30:
                title = title[:30]

            elapsed_time = time.time() - start_time
            self.logger.info(f"会话标题生成成功: '{title}', 响应时间={elapsed_time:.2f}s")

            return title

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.warning(
                f"会话标题生成失败: {e}, 耗时={elapsed_time:.2f}s, 使用默认标题"
            )
            # 如果生成失败，返回截取的用户消息
            return user_message[:30] if len(user_message) > 30 else user_message
