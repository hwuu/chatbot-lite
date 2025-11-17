"""session_manager.py 的单元测试"""

import json
import time
from pathlib import Path

import pytest

from clichat.session_manager import SessionManager


class TestSessionManager:
    """测试 SessionManager"""

    @pytest.fixture
    def temp_history_dir(self, tmp_path):
        """创建临时历史目录"""
        return str(tmp_path / "test_history")

    @pytest.fixture
    def manager(self, temp_history_dir):
        """创建 SessionManager 实例"""
        return SessionManager(temp_history_dir)

    def test_init_creates_directory(self, temp_history_dir):
        """测试初始化时创建目录"""
        manager = SessionManager(temp_history_dir)
        assert Path(temp_history_dir).exists()
        assert Path(temp_history_dir).is_dir()

    def test_create_session(self, manager):
        """测试创建会话"""
        system_prompt = "You are a helpful assistant."
        session_id = manager.create_session(system_prompt)

        # 验证返回的 session_id 格式
        assert len(session_id) == 22  # YYYYMMDD_HHMMSS_ffffff
        assert session_id.count("_") == 2  # 两个下划线

        # 验证会话文件已创建
        session_path = manager.history_dir / f"session_{session_id}.json"
        assert session_path.exists()

        # 验证会话内容
        session_data = manager.load_session(session_id)
        assert session_data["session_id"] == session_id
        assert session_data["title"] == "(空会话)"
        assert len(session_data["messages"]) == 1
        assert session_data["messages"][0]["role"] == "system"
        assert session_data["messages"][0]["content"] == system_prompt
        assert session_data["total_tokens"] > 0

    def test_load_session(self, manager):
        """测试加载会话"""
        system_prompt = "Test prompt"
        session_id = manager.create_session(system_prompt)

        # 加载会话
        session_data = manager.load_session(session_id)

        assert session_data["session_id"] == session_id
        assert session_data["messages"][0]["content"] == system_prompt

    def test_load_nonexistent_session(self, manager):
        """测试加载不存在的会话"""
        with pytest.raises(FileNotFoundError, match="会话不存在"):
            manager.load_session("nonexistent_id")

    def test_save_message_user(self, manager):
        """测试保存用户消息"""
        session_id = manager.create_session("System prompt")

        # 添加用户消息
        user_message = "Hello, how are you?"
        manager.save_message(session_id, "user", user_message)

        # 验证消息已保存
        session_data = manager.load_session(session_id)
        assert len(session_data["messages"]) == 2
        assert session_data["messages"][1]["role"] == "user"
        assert session_data["messages"][1]["content"] == user_message

    def test_save_message_assistant(self, manager):
        """测试保存助手消息"""
        session_id = manager.create_session("System prompt")
        manager.save_message(session_id, "user", "Question")

        # 添加助手回复
        assistant_message = "I'm doing well, thank you!"
        manager.save_message(session_id, "assistant", assistant_message)

        # 验证消息已保存
        session_data = manager.load_session(session_id)
        assert len(session_data["messages"]) == 3
        assert session_data["messages"][2]["role"] == "assistant"
        assert session_data["messages"][2]["content"] == assistant_message

    def test_save_message_updates_tokens(self, manager):
        """测试保存消息时更新 token 计数"""
        session_id = manager.create_session("System prompt")
        initial_tokens = manager.load_session(session_id)["total_tokens"]

        # 添加消息
        manager.save_message(session_id, "user", "Test message")

        # 验证 token 数量增加
        session_data = manager.load_session(session_id)
        assert session_data["total_tokens"] > initial_tokens

    def test_update_title_with_long_message(self, manager):
        """测试更新标题方法"""
        session_id = manager.create_session("System prompt")

        # 添加长消息
        long_message = "This is a very long message that exceeds thirty characters"
        manager.save_message(session_id, "user", long_message)

        # 手动更新标题
        manager.update_title(session_id, "Custom Title")

        # 验证标题被更新
        session_data = manager.load_session(session_id)
        assert session_data["title"] == "Custom Title"

    def test_list_sessions_empty(self, manager):
        """测试列出空会话列表"""
        sessions = manager.list_sessions()
        assert sessions == []

    def test_list_sessions(self, manager):
        """测试列出会话"""
        # 创建多个会话
        id1 = manager.create_session("Prompt 1")
        time.sleep(0.01)  # 确保时间戳不同
        id2 = manager.create_session("Prompt 2")

        # 添加消息以更新标题
        manager.save_message(id1, "user", "First chat")
        manager.update_title(id1, "First chat")
        time.sleep(0.01)
        manager.save_message(id2, "user", "Second chat")
        manager.update_title(id2, "Second chat")

        # 列出会话
        sessions = manager.list_sessions()

        assert len(sessions) == 2
        # 应该按更新时间倒序
        assert sessions[0]["session_id"] == id2
        assert sessions[1]["session_id"] == id1
        assert sessions[0]["title"] == "Second chat"
        assert sessions[1]["title"] == "First chat"

    def test_list_sessions_with_limit(self, manager):
        """测试限制列出会话数量"""
        # 创建 3 个会话
        for i in range(3):
            manager.create_session(f"Prompt {i}")
            time.sleep(0.01)

        # 限制返回 2 个
        sessions = manager.list_sessions(limit=2)
        assert len(sessions) == 2

    def test_search_sessions_by_title(self, manager):
        """测试按标题搜索会话"""
        id1 = manager.create_session("System")
        id2 = manager.create_session("System")

        manager.save_message(id1, "user", "Python tutorial")
        manager.update_title(id1, "Python tutorial")
        manager.save_message(id2, "user", "JavaScript guide")
        manager.update_title(id2, "JavaScript guide")

        # 搜索 "Python"
        results = manager.search_sessions("Python")
        assert len(results) == 1
        assert results[0]["session_id"] == id1
        assert results[0]["match_type"] == "title"

    def test_search_sessions_by_content(self, manager):
        """测试按内容搜索会话"""
        id1 = manager.create_session("System")
        manager.save_message(id1, "user", "First message")
        manager.save_message(id1, "assistant", "I can help with Python programming")

        # 搜索 "Python"
        results = manager.search_sessions("Python")
        assert len(results) == 1
        assert results[0]["session_id"] == id1
        assert results[0]["match_type"] == "content"
        assert "match_preview" in results[0]

    def test_search_sessions_case_insensitive(self, manager):
        """测试搜索不区分大小写"""
        session_id = manager.create_session("System")
        manager.save_message(session_id, "user", "HELLO World")

        # 使用小写搜索
        results = manager.search_sessions("hello")
        assert len(results) == 1

        # 使用大写搜索
        results = manager.search_sessions("WORLD")
        assert len(results) == 1

    def test_search_sessions_no_results(self, manager):
        """测试搜索无结果"""
        session_id = manager.create_session("System")
        manager.save_message(session_id, "user", "Test message")

        results = manager.search_sessions("nonexistent")
        assert results == []

    def test_delete_session(self, manager):
        """测试删除会话"""
        session_id = manager.create_session("System")

        # 验证会话存在
        assert manager.load_session(session_id) is not None

        # 删除会话
        manager.delete_session(session_id)

        # 验证会话已删除
        with pytest.raises(FileNotFoundError):
            manager.load_session(session_id)

    def test_delete_nonexistent_session(self, manager):
        """测试删除不存在的会话"""
        with pytest.raises(FileNotFoundError, match="会话不存在"):
            manager.delete_session("nonexistent_id")

    def test_session_data_structure(self, manager):
        """测试会话数据结构完整性"""
        session_id = manager.create_session("System prompt")
        manager.save_message(session_id, "user", "User message")
        manager.save_message(session_id, "assistant", "Assistant reply")

        session_data = manager.load_session(session_id)

        # 验证必要字段存在
        assert "session_id" in session_data
        assert "created_at" in session_data
        assert "updated_at" in session_data
        assert "title" in session_data
        assert "messages" in session_data
        assert "total_tokens" in session_data

        # 验证消息结构
        for msg in session_data["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert "timestamp" in msg
            assert "tokens" in msg
