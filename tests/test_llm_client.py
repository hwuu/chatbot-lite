"""llm_client.py 的单元测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from openai.types.chat.chat_completion import Choice as CompletionChoice
from openai.types.chat.chat_completion_chunk import (
    Choice as ChunkChoice,
    ChoiceDelta,
)
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from chatbot_lite.config import LLMConfig
from chatbot_lite.llm_client import LLMClient


class TestLLMClient:
    """测试 LLMClient"""

    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return LLMConfig(
            api_base="http://localhost:11434/v1",
            model="test-model",
            api_key="test-key",
            temperature=0.7,
            max_tokens=2000,
        )

    @pytest.fixture
    def client(self, config):
        """创建 LLMClient 实例"""
        return LLMClient(config)

    @pytest.mark.asyncio
    async def test_init(self, config):
        """测试初始化"""
        client = LLMClient(config)
        assert client.config == config
        assert isinstance(client.client, AsyncOpenAI)
        await client.close()

    @pytest.mark.asyncio
    async def test_chat_stream_success(self, client):
        """测试流式对话成功"""
        # 创建 mock chunks
        mock_chunks = [
            ChatCompletionChunk(
                id="chunk1",
                model="test-model",
                object="chat.completion.chunk",
                created=1234567890,
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content="Hello", role="assistant"),
                        finish_reason=None,
                    )
                ],
            ),
            ChatCompletionChunk(
                id="chunk2",
                model="test-model",
                object="chat.completion.chunk",
                created=1234567891,
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content=" world", role=None),
                        finish_reason=None,
                    )
                ],
            ),
            ChatCompletionChunk(
                id="chunk3",
                model="test-model",
                object="chat.completion.chunk",
                created=1234567892,
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content="!", role=None),
                        finish_reason="stop",
                    )
                ],
            ),
        ]

        # Mock 异步迭代器
        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        # Mock create 方法
        with patch.object(
            client.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_stream(),
        ):
            # 收集 chunks
            received_chunks = []

            async def on_chunk(chunk: str):
                received_chunks.append(chunk)

            # 调用
            messages = [{"role": "user", "content": "Test"}]
            result = await client.chat_stream(messages, on_chunk)

            # 验证最终结果
            assert result == "Hello world!"
            # 验证所有 chunks 拼接后的结果正确
            assert "".join(received_chunks) == "Hello world!"
            # 验证至少收到了一些 chunks
            assert len(received_chunks) > 0

    @pytest.mark.asyncio
    async def test_chat_stream_empty_delta(self, client):
        """测试处理空的 delta 内容"""
        mock_chunks = [
            ChatCompletionChunk(
                id="chunk1",
                model="test-model",
                object="chat.completion.chunk",
                created=1234567890,
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content="Hello", role="assistant"),
                        finish_reason=None,
                    )
                ],
            ),
            ChatCompletionChunk(
                id="chunk2",
                model="test-model",
                object="chat.completion.chunk",
                created=1234567891,
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content=None, role=None),  # 空内容
                        finish_reason=None,
                    )
                ],
            ),
            ChatCompletionChunk(
                id="chunk3",
                model="test-model",
                object="chat.completion.chunk",
                created=1234567892,
                choices=[
                    ChunkChoice(
                        index=0,
                        delta=ChoiceDelta(content=" world", role=None),
                        finish_reason="stop",
                    )
                ],
            ),
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        with patch.object(
            client.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_stream(),
        ):
            received_chunks = []

            async def on_chunk(chunk: str):
                received_chunks.append(chunk)

            messages = [{"role": "user", "content": "Test"}]
            result = await client.chat_stream(messages, on_chunk)

            # 空内容应该被跳过
            assert result == "Hello world"
            assert received_chunks == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_chat_stream_api_error(self, client):
        """测试 API 错误处理"""
        # Mock API 错误
        with patch.object(
            client.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=Exception("API Error"),
        ):
            async def on_chunk(chunk: str):
                pass

            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(Exception, match="LLM API 调用失败"):
                await client.chat_stream(messages, on_chunk)

    @pytest.mark.asyncio
    async def test_chat_success(self, client):
        """测试非流式对话成功"""
        # Mock 响应
        mock_response = ChatCompletion(
            id="completion1",
            model="test-model",
            object="chat.completion",
            created=1234567890,
            choices=[
                CompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant", content="Hello from LLM"
                    ),
                    finish_reason="stop",
                )
            ],
        )

        with patch.object(
            client.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            messages = [{"role": "user", "content": "Test"}]
            result = await client.chat(messages)

            assert result == "Hello from LLM"

    @pytest.mark.asyncio
    async def test_chat_with_think_tags(self, client):
        """测试非流式对话过滤 think 标签"""
        # Mock 响应包含 think 标签
        mock_response = ChatCompletion(
            id="completion1",
            model="test-model",
            object="chat.completion",
            created=1234567890,
            choices=[
                CompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content="<think>internal reasoning</think>Hello from LLM"
                    ),
                    finish_reason="stop",
                )
            ],
        )

        with patch.object(
            client.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            messages = [{"role": "user", "content": "Test"}]
            result = await client.chat(messages)

            # think 标签应该被过滤掉
            assert result == "Hello from LLM"
            assert "<think>" not in result

    @pytest.mark.asyncio
    async def test_chat_api_error(self, client):
        """测试非流式对话 API 错误"""
        with patch.object(
            client.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            side_effect=Exception("API Error"),
        ):
            messages = [{"role": "user", "content": "Test"}]

            with pytest.raises(Exception, match="LLM API 调用失败"):
                await client.chat(messages)

    @pytest.mark.asyncio
    async def test_close(self, client):
        """测试关闭客户端"""
        await client.close()
        # 验证 client 已关闭（这里只是确保没有异常）
