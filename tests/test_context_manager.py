"""context_manager.py 的单元测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from clichat.config import AppConfig, LLMConfig
from clichat.context_manager import ContextManager
from clichat.llm_client import LLMClient


class TestContextManager:
    """测试 ContextManager"""

    @pytest.fixture
    def llm_config(self):
        """创建 LLM 配置"""
        return LLMConfig(
            api_base="http://localhost:11434/v1",
            model="test-model",
            max_tokens=2000,
        )

    @pytest.fixture
    def app_config(self):
        """创建应用配置"""
        return AppConfig(
            history_dir="/tmp/test",
            compress_threshold=0.85,
            compress_summary_tokens=300,
        )

    @pytest.fixture
    def llm_client(self, llm_config):
        """创建 LLM 客户端"""
        return LLMClient(llm_config)

    @pytest.fixture
    def manager(self, app_config, llm_client):
        """创建 ContextManager 实例"""
        return ContextManager(app_config, llm_client)

    def create_session(self, message_count: int, tokens_per_message: int = 50) -> dict:
        """
        创建测试会话

        Args:
            message_count: 消息数量（不包括 system）
            tokens_per_message: 每条消息的 token 数

        Returns:
            会话数据字典
        """
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant.",
                "tokens": 50,
            }
        ]

        for i in range(message_count):
            # 交替添加 user 和 assistant 消息
            role = "user" if i % 2 == 0 else "assistant"
            messages.append(
                {
                    "role": role,
                    "content": f"Message {i + 1}",
                    "tokens": tokens_per_message,
                }
            )

        total_tokens = 50 + message_count * tokens_per_message

        return {
            "session_id": "test_session",
            "messages": messages,
            "total_tokens": total_tokens,
        }

    @pytest.mark.asyncio
    async def test_init(self, app_config, llm_client):
        """测试初始化"""
        manager = ContextManager(app_config, llm_client)
        assert manager.config == app_config
        assert manager.llm_client == llm_client
        assert manager._compressed_summary is None
        assert manager._recent_message_count == 10

    @pytest.mark.asyncio
    async def test_below_threshold_returns_all(self, manager):
        """测试未超过阈值时返回全部消息"""
        # 创建小会话（总 tokens < 阈值）
        # 阈值 = 2000 * 0.85 = 1700
        session = self.create_session(message_count=10, tokens_per_message=50)
        # 总 tokens = 50 + 10 * 50 = 550

        current_input_tokens = 100  # 总共 650 < 1700

        result = await manager.get_context_messages(session, current_input_tokens)

        # 应该返回所有消息
        assert len(result) == len(session["messages"])
        assert result == session["messages"]

    @pytest.mark.asyncio
    async def test_above_threshold_triggers_compression(self, manager):
        """测试超过阈值时触发压缩"""
        # 创建大会话
        # 阈值 = 2000 * 0.85 = 1700
        session = self.create_session(message_count=30, tokens_per_message=50)
        # 总 tokens = 50 + 30 * 50 = 1550

        current_input_tokens = 200  # 总共 1750 > 1700，触发压缩

        # Mock LLM 压缩响应
        manager.llm_client.chat = AsyncMock(
            return_value="This is a compressed summary of the conversation."
        )

        result = await manager.get_context_messages(session, current_input_tokens)

        # 验证调用了压缩
        manager.llm_client.chat.assert_called_once()

        # 验证结果结构
        # 应该包含：system + 摘要 + 最近 10 条消息
        assert len(result) == 1 + 1 + 10  # system + summary + recent 10
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."

        # 验证摘要
        assert result[1]["role"] == "system"
        assert "[Previous conversation summary]" in result[1]["content"]
        assert "compressed summary" in result[1]["content"]

        # 验证最近消息
        for i in range(2, 12):
            # 最近 10 条消息应该是原始的第 21-30 条
            original_index = 20 + (i - 2) + 1  # +1 因为 session 的第 0 条是 system
            assert result[i]["content"] == session["messages"][original_index]["content"]

    @pytest.mark.asyncio
    async def test_compression_cached(self, manager):
        """测试压缩结果被缓存"""
        session = self.create_session(message_count=30, tokens_per_message=50)
        current_input_tokens = 200

        # Mock LLM 压缩响应
        manager.llm_client.chat = AsyncMock(return_value="Cached summary")

        # 第一次调用
        result1 = await manager.get_context_messages(session, current_input_tokens)
        assert manager.llm_client.chat.call_count == 1

        # 第二次调用（应该使用缓存）
        result2 = await manager.get_context_messages(session, current_input_tokens)
        assert manager.llm_client.chat.call_count == 1  # 没有增加

        # 验证两次结果一致
        assert len(result1) == len(result2)
        assert result1[1]["content"] == result2[1]["content"]

    @pytest.mark.asyncio
    async def test_few_messages_no_compression(self, manager):
        """测试消息少于保留数量时不压缩"""
        # 创建只有 8 条消息的会话（少于 10）
        session = self.create_session(message_count=8, tokens_per_message=200)
        # 总 tokens = 50 + 8 * 200 = 1650

        current_input_tokens = 100  # 总共 1750 > 1700，但消息太少

        result = await manager.get_context_messages(session, current_input_tokens)

        # 应该返回所有消息（不压缩）
        assert len(result) == len(session["messages"])
        assert result == session["messages"]

    @pytest.mark.asyncio
    async def test_compression_failure_fallback(self, manager):
        """测试压缩失败时的降级处理"""
        session = self.create_session(message_count=30, tokens_per_message=50)
        current_input_tokens = 200

        # Mock LLM 抛出异常
        manager.llm_client.chat = AsyncMock(side_effect=Exception("LLM error"))

        result = await manager.get_context_messages(session, current_input_tokens)

        # 应该仍然返回结果（使用降级摘要）
        assert len(result) > 0
        assert result[1]["role"] == "system"
        assert "[Compression failed" in result[1]["content"]

    @pytest.mark.asyncio
    async def test_reset_compression(self, manager):
        """测试重置压缩缓存"""
        session = self.create_session(message_count=30, tokens_per_message=50)
        current_input_tokens = 200

        # Mock LLM
        manager.llm_client.chat = AsyncMock(return_value="First summary")

        # 触发压缩
        await manager.get_context_messages(session, current_input_tokens)
        assert manager._compressed_summary is not None
        assert manager.llm_client.chat.call_count == 1

        # 重置
        manager.reset_compression()
        assert manager._compressed_summary is None

        # 再次触发（应该重新压缩）
        manager.llm_client.chat = AsyncMock(return_value="Second summary")
        result = await manager.get_context_messages(session, current_input_tokens)
        assert manager.llm_client.chat.call_count == 1
        assert "Second summary" in result[1]["content"]

    @pytest.mark.asyncio
    async def test_get_compression_status(self, manager):
        """测试获取压缩状态"""
        # 初始状态
        status = manager.get_compression_status()
        assert status["has_compressed"] is False
        assert status["summary_length"] == 0
        assert status["recent_message_count"] == 10
        assert status["threshold"] == 0.85

        # 触发压缩后
        session = self.create_session(message_count=30, tokens_per_message=50)
        manager.llm_client.chat = AsyncMock(return_value="Test summary")

        await manager.get_context_messages(session, 200)

        status = manager.get_compression_status()
        assert status["has_compressed"] is True
        assert status["summary_length"] > 0

    @pytest.mark.asyncio
    async def test_compress_messages_prompt_format(self, manager):
        """测试压缩提示词格式正确"""
        messages = [
            {"role": "user", "content": "Hello", "tokens": 10},
            {"role": "assistant", "content": "Hi there", "tokens": 10},
        ]

        manager.llm_client.chat = AsyncMock(return_value="Summary")

        await manager._compress_messages(messages)

        # 验证调用参数
        call_args = manager.llm_client.chat.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["role"] == "system"
        assert "conversation summarizer" in call_args[0]["content"].lower()

        assert call_args[1]["role"] == "user"
        assert "user: Hello" in call_args[1]["content"]
        assert "assistant: Hi there" in call_args[1]["content"]
        assert str(manager.config.compress_summary_tokens) in call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_exact_threshold_boundary(self, manager):
        """测试阈值边界情况"""
        # 创建略低于阈值的会话
        # 阈值 = 2000 * 0.85 = 1700
        session = self.create_session(message_count=32, tokens_per_message=50)
        # 总 tokens = 50 + 32 * 50 = 1650

        current_input_tokens = 49  # 总共 1699，略低于阈值

        # 阈值判断是 < threshold，所以 1699 < 1700 为 True，不压缩
        result = await manager.get_context_messages(session, current_input_tokens)

        # 应该返回所有消息（不压缩）
        assert len(result) == len(session["messages"])
