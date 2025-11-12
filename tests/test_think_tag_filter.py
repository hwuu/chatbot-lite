"""ThinkTagFilter 的单元测试"""

import pytest

from chatbot_lite.llm_client import ThinkTagFilter


class TestThinkTagFilter:
    """测试 ThinkTagFilter"""

    def test_no_think_tags(self):
        """测试没有 think 标签的情况"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("Hello, world!")
        result += filter.finalize()
        assert result == "Hello, world!"

    def test_simple_think_tag(self):
        """测试简单的完整 think 标签"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("<think>internal thoughts</think>Hello!")
        result += filter.finalize()
        assert result == "Hello!"

    def test_think_tag_at_end(self):
        """测试 think 标签在结尾"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("Hello!<think>internal thoughts</think>")
        result += filter.finalize()
        assert result == "Hello!"

    def test_think_tag_in_middle(self):
        """测试 think 标签在中间"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("Start <think>thinking</think> End")
        result += filter.finalize()
        assert result == "Start  End"

    def test_multiple_think_tags(self):
        """测试多个 think 标签"""
        filter = ThinkTagFilter()
        result = filter.process_chunk(
            "<think>first</think>A<think>second</think>B<think>third</think>C"
        )
        result += filter.finalize()
        assert result == "ABC"

    def test_think_tag_across_chunks(self):
        """测试跨 chunk 的 think 标签"""
        filter = ThinkTagFilter()
        result = ""
        result += filter.process_chunk("Hello <thi")
        result += filter.process_chunk("nk>internal")
        result += filter.process_chunk(" thoughts</thi")
        result += filter.process_chunk("nk> World!")
        result += filter.finalize()
        assert result == "Hello  World!"

    def test_content_before_and_after_think(self):
        """测试 think 标签前后有内容"""
        filter = ThinkTagFilter()
        result = ""
        result += filter.process_chunk("Before ")
        result += filter.process_chunk("<think>thinking</think>")
        result += filter.process_chunk(" After")
        result += filter.finalize()
        assert result == "Before  After"

    def test_partial_opening_tag_at_boundary(self):
        """测试开始标签被分割到不同 chunk"""
        filter = ThinkTagFilter()
        result = ""
        result += filter.process_chunk("Text <")
        result += filter.process_chunk("think>hidden</think>visible")
        result += filter.finalize()
        assert result == "Text visible"

    def test_partial_closing_tag_at_boundary(self):
        """测试结束标签被分割到不同 chunk"""
        filter = ThinkTagFilter()
        result = ""
        result += filter.process_chunk("<think>hidden</")
        result += filter.process_chunk("think>visible")
        result += filter.finalize()
        assert result == "visible"

    def test_unclosed_think_tag(self):
        """测试未闭合的 think 标签"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("Start <think>thinking...")
        result += filter.finalize()
        assert result == "Start "

    def test_empty_think_tag(self):
        """测试空的 think 标签"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("Before<think></think>After")
        result += filter.finalize()
        assert result == "BeforeAfter"

    def test_nested_like_tags(self):
        """测试类似嵌套的情况（实际不应该嵌套）"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("<think>outer<think>inner</think>still hidden</think>visible")
        result += filter.finalize()
        # 第一个 </think> 会关闭第一个 <think>
        assert result == "still hidden</think>visible"

    def test_only_think_content(self):
        """测试只有 think 标签内容"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("<think>only thinking</think>")
        result += filter.finalize()
        assert result == ""

    def test_multiple_chunks_with_think(self):
        """测试多个 chunk 中包含完整和部分 think 标签"""
        filter = ThinkTagFilter()
        result = ""
        result += filter.process_chunk("A")
        result += filter.process_chunk("<think>hidden1</think>")
        result += filter.process_chunk("B")
        result += filter.process_chunk("<thi")
        result += filter.process_chunk("nk>hidden2</think>")
        result += filter.process_chunk("C")
        result += filter.finalize()
        assert result == "ABC"

    def test_long_think_content(self):
        """测试长 think 标签内容"""
        filter = ThinkTagFilter()
        long_think = "<think>" + "x" * 1000 + "</think>"
        result = filter.process_chunk("Before " + long_think + " After")
        result += filter.finalize()
        assert result == "Before  After"

    def test_think_with_newlines(self):
        """测试包含换行的 think 标签"""
        filter = ThinkTagFilter()
        result = filter.process_chunk("Start<think>\nthinking\nprocess\n</think>End")
        result += filter.finalize()
        assert result == "StartEnd"
