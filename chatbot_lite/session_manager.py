"""会话管理模块

负责对话历史的 CRUD 操作、搜索等功能。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from chatbot_lite.utils import count_tokens, truncate_text


class SessionManager:
    """会话管理器"""

    def __init__(self, history_dir: str):
        """
        初始化会话管理器

        Args:
            history_dir: 对话历史存储目录的绝对路径
        """
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, system_prompt: str) -> str:
        """
        创建新会话

        Args:
            system_prompt: 系统提示词

        Returns:
            session_id: 新创建的会话 ID
        """
        # 生成会话 ID（基于时间戳，包含微秒以确保唯一性）
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        # 初始化会话数据
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "title": "New Chat",  # 默认标题，首次用户消息后会更新
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                    "timestamp": datetime.now().isoformat(),
                    "tokens": count_tokens(system_prompt),
                }
            ],
            "total_tokens": count_tokens(system_prompt),
        }

        # 保存到文件
        self._save_session(session_id, session_data)

        return session_id

    def load_session(self, session_id: str) -> Dict:
        """
        加载指定会话

        Args:
            session_id: 会话 ID

        Returns:
            会话数据字典

        Raises:
            FileNotFoundError: 会话不存在
        """
        session_path = self.history_dir / f"session_{session_id}.json"

        if not session_path.exists():
            raise FileNotFoundError(f"会话不存在: {session_id}")

        with open(session_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self, limit: Optional[int] = None) -> List[Dict]:
        """
        列出所有会话（按更新时间倒序）

        Args:
            limit: 限制返回数量，None 表示不限制

        Returns:
            会话摘要列表，每个元素包含 session_id, title, updated_at
        """
        sessions = []

        for session_path in self.history_dir.glob("session_*.json"):
            try:
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions.append(
                        {
                            "session_id": data["session_id"],
                            "title": data["title"],
                            "updated_at": data["updated_at"],
                            "created_at": data["created_at"],
                            "message_count": len(data["messages"]) - 1,  # 减去 system
                        }
                    )
            except (json.JSONDecodeError, KeyError):
                # 跳过损坏的文件
                continue

        # 按更新时间倒序排列
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)

        if limit:
            return sessions[:limit]

        return sessions

    def search_sessions(self, keyword: str) -> List[Dict]:
        """
        全文搜索会话（搜索标题和消息内容）

        Args:
            keyword: 搜索关键字

        Returns:
            匹配的会话列表
        """
        keyword_lower = keyword.lower()
        results = []

        for session_path in self.history_dir.glob("session_*.json"):
            try:
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # 搜索标题
                    if keyword_lower in data["title"].lower():
                        results.append(
                            {
                                "session_id": data["session_id"],
                                "title": data["title"],
                                "updated_at": data["updated_at"],
                                "match_type": "title",
                            }
                        )
                        continue

                    # 搜索消息内容
                    for msg in data["messages"]:
                        if keyword_lower in msg["content"].lower():
                            results.append(
                                {
                                    "session_id": data["session_id"],
                                    "title": data["title"],
                                    "updated_at": data["updated_at"],
                                    "match_type": "content",
                                    "match_preview": truncate_text(
                                        msg["content"], 100
                                    ),
                                }
                            )
                            break
            except (json.JSONDecodeError, KeyError):
                continue

        # 按更新时间倒序排列
        results.sort(key=lambda x: x["updated_at"], reverse=True)

        return results

    def save_message(
        self, session_id: str, role: str, content: str, update_title: bool = False
    ):
        """
        追加消息到会话

        Args:
            session_id: 会话 ID
            role: 消息角色（user 或 assistant）
            content: 消息内容
            update_title: 是否更新会话标题（首次用户消息时为 True）

        Raises:
            FileNotFoundError: 会话不存在
        """
        # 加载会话
        session_data = self.load_session(session_id)

        # 添加新消息
        tokens = count_tokens(content)
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "tokens": tokens,
        }
        session_data["messages"].append(message)

        # 更新总 token 数
        session_data["total_tokens"] += tokens

        # 更新时间戳
        session_data["updated_at"] = datetime.now().isoformat()

        # 更新标题（如果需要且当前是默认标题）
        if update_title and session_data["title"] == "New Chat" and role == "user":
            # 取用户消息的前 30 个字符作为标题
            session_data["title"] = truncate_text(content, 30, suffix="...")

        # 保存
        self._save_session(session_id, session_data)

    def delete_session(self, session_id: str):
        """
        删除会话

        Args:
            session_id: 会话 ID

        Raises:
            FileNotFoundError: 会话不存在
        """
        session_path = self.history_dir / f"session_{session_id}.json"

        if not session_path.exists():
            raise FileNotFoundError(f"会话不存在: {session_id}")

        session_path.unlink()

    def _save_session(self, session_id: str, session_data: Dict):
        """
        保存会话到文件

        Args:
            session_id: 会话 ID
            session_data: 会话数据
        """
        session_path = self.history_dir / f"session_{session_id}.json"

        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
