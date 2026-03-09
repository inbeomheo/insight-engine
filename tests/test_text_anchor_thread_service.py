"""텍스트 앵커 쓰레드 서비스 테스트"""

import unittest
from services.text_anchor_thread_service import (
    TextAnchor, ThreadComment,
    create_anchor, add_comment, resolve_thread, get_active_threads,
)


class TestCreateAnchor(unittest.TestCase):
    """create_anchor 테스트"""

    def test_create_anchor_basic(self):
        """기본 앵커 생성"""
        anchor = create_anchor("doc_1", 0, 10, "선택 텍스트")
        self.assertTrue(anchor.anchor_id.startswith("anchor_"))
        self.assertEqual(anchor.document_id, "doc_1")
        self.assertEqual(anchor.start_offset, 0)
        self.assertEqual(anchor.end_offset, 10)
        self.assertEqual(anchor.selected_text, "선택 텍스트")

    def test_negative_offset_raises(self):
        """음수 오프셋은 ValueError"""
        with self.assertRaises(ValueError):
            create_anchor("doc_1", -1, 10, "텍스트")

    def test_start_gte_end_raises(self):
        """시작 >= 끝이면 ValueError"""
        with self.assertRaises(ValueError):
            create_anchor("doc_1", 10, 10, "텍스트")
        with self.assertRaises(ValueError):
            create_anchor("doc_1", 15, 10, "텍스트")

    def test_empty_text_raises(self):
        """빈 텍스트는 ValueError"""
        with self.assertRaises(ValueError):
            create_anchor("doc_1", 0, 5, "   ")


class TestAddComment(unittest.TestCase):
    """add_comment 테스트"""

    def test_add_comment_basic(self):
        """기본 코멘트 추가"""
        comment = add_comment("anchor_1", "작성자A", "코멘트 내용")
        self.assertTrue(comment.comment_id.startswith("comment_"))
        self.assertEqual(comment.anchor_id, "anchor_1")
        self.assertEqual(comment.author, "작성자A")
        self.assertFalse(comment.resolved)

    def test_empty_author_raises(self):
        """빈 작성자는 ValueError"""
        with self.assertRaises(ValueError):
            add_comment("anchor_1", "  ", "내용")

    def test_empty_content_raises(self):
        """빈 내용은 ValueError"""
        with self.assertRaises(ValueError):
            add_comment("anchor_1", "작성자", "   ")

    def test_author_trimmed(self):
        """작성자 이름 양쪽 공백 제거"""
        comment = add_comment("a1", "  작성자  ", "내용")
        self.assertEqual(comment.author, "작성자")

    def test_timestamp_set(self):
        """타임스탬프 설정됨"""
        comment = add_comment("a1", "저자", "코멘트")
        self.assertTrue(len(comment.timestamp) > 0)


class TestResolveThread(unittest.TestCase):
    """resolve_thread 테스트"""

    def test_resolve_marks_all_as_resolved(self):
        """해당 앵커의 모든 코멘트가 resolved=True"""
        c1 = add_comment("anchor_1", "A", "코멘트1")
        c2 = add_comment("anchor_1", "B", "코멘트2")
        c3 = add_comment("anchor_2", "C", "다른 앵커")

        resolved = resolve_thread([c1, c2, c3], "anchor_1")
        self.assertTrue(resolved[0].resolved)
        self.assertTrue(resolved[1].resolved)
        self.assertFalse(resolved[2].resolved)

    def test_resolve_preserves_other_threads(self):
        """다른 앵커의 코멘트는 영향 없음"""
        c1 = add_comment("a1", "A", "코멘트")
        c2 = add_comment("a2", "B", "다른 앵커")

        resolved = resolve_thread([c1, c2], "a1")
        self.assertFalse(resolved[1].resolved)

    def test_resolve_empty_list(self):
        """빈 목록 처리"""
        resolved = resolve_thread([], "anchor_1")
        self.assertEqual(len(resolved), 0)


class TestGetActiveThreads(unittest.TestCase):
    """get_active_threads 테스트"""

    def test_active_threads_count(self):
        """미해결 쓰레드 집계"""
        c1 = add_comment("a1", "A", "코멘트1")
        c2 = add_comment("a1", "B", "코멘트2")
        c3 = add_comment("a2", "C", "다른 쓰레드")

        threads = get_active_threads([c1, c2, c3])
        self.assertEqual(len(threads), 2)

        # a1 앵커는 코멘트 2개
        a1_thread = next(t for t in threads if t["anchor_id"] == "a1")
        self.assertEqual(a1_thread["comment_count"], 2)

    def test_resolved_threads_excluded(self):
        """해결된 쓰레드는 제외"""
        c1 = add_comment("a1", "A", "코멘트")
        resolved = resolve_thread([c1], "a1")

        threads = get_active_threads(resolved)
        self.assertEqual(len(threads), 0)

    def test_mixed_resolved_and_active(self):
        """해결/미해결 혼합"""
        c1 = add_comment("a1", "A", "코멘트1")
        c2 = add_comment("a2", "B", "코멘트2")
        resolved = resolve_thread([c1, c2], "a1")

        threads = get_active_threads(resolved)
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["anchor_id"], "a2")

    def test_empty_comments_returns_empty(self):
        """빈 코멘트 목록"""
        threads = get_active_threads([])
        self.assertEqual(len(threads), 0)


if __name__ == "__main__":
    unittest.main()
