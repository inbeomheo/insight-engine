"""AI 메모리 레이어 단위 테스트"""
import os
import shutil
import tempfile
import unittest

from services.data.memory_service import MemoryService, MAX_FEEDBACK_HISTORY


class TestMemoryService(unittest.TestCase):
    """MemoryService 단위 테스트"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.service = MemoryService(store_path=self.tmpdir)
        self.uid = "test-user"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_memory(self):
        """초기 상태는 빈 딕셔너리"""
        memory = self.service.get_memory(self.uid)
        self.assertEqual(memory, {})

    def test_update_and_get(self):
        """메모리 업데이트 후 조회"""
        self.service.update_memory(self.uid, "preferred_topics", ["AI", "Python"])
        memory = self.service.get_memory(self.uid)
        self.assertEqual(memory["preferred_topics"], ["AI", "Python"])

    def test_get_value(self):
        """특정 키 조회"""
        self.service.update_memory(self.uid, "preferred_tone", "전문적")
        tone = self.service.get_value(self.uid, "preferred_tone")
        self.assertEqual(tone, "전문적")

    def test_get_value_default(self):
        """없는 키는 기본값 반환"""
        val = self.service.get_value(self.uid, "nonexistent", "default")
        self.assertEqual(val, "default")

    def test_feedback_history_append(self):
        """feedback_history는 append 방식"""
        self.service.update_memory(self.uid, "feedback_history", "좋은 글이었어요")
        self.service.update_memory(self.uid, "feedback_history", "더 길게 써주세요")
        history = self.service.get_value(self.uid, "feedback_history", [])
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0], "좋은 글이었어요")

    def test_feedback_history_max_limit(self):
        """feedback_history 최대 개수 제한"""
        for i in range(MAX_FEEDBACK_HISTORY + 5):
            self.service.update_memory(self.uid, "feedback_history", f"피드백 {i}")
        history = self.service.get_value(self.uid, "feedback_history", [])
        self.assertEqual(len(history), MAX_FEEDBACK_HISTORY)

    def test_delete_key(self):
        """특정 키 삭제"""
        self.service.update_memory(self.uid, "preferred_tone", "전문적")
        self.service.delete_key(self.uid, "preferred_tone")
        val = self.service.get_value(self.uid, "preferred_tone")
        self.assertIsNone(val)

    def test_clear(self):
        """전체 초기화"""
        self.service.update_memory(self.uid, "preferred_topics", ["AI"])
        self.service.clear(self.uid)
        memory = self.service.get_memory(self.uid)
        self.assertEqual(memory, {})

    def test_persistence(self):
        """파일 저장 후 새 인스턴스에서 로드"""
        self.service.update_memory(self.uid, "language", "ko")

        # 새 인스턴스로 로드
        service2 = MemoryService(store_path=self.tmpdir)
        val = service2.get_value(self.uid, "language")
        self.assertEqual(val, "ko")

    def test_build_prompt_context_empty(self):
        """빈 메모리는 빈 문자열 반환"""
        ctx = self.service.build_prompt_context(self.uid)
        self.assertEqual(ctx, "")

    def test_build_prompt_context_with_data(self):
        """메모리가 있으면 컨텍스트 문자열 반환"""
        self.service.update_memory(self.uid, "preferred_topics", ["AI", "블록체인"])
        self.service.update_memory(self.uid, "preferred_tone", "전문적")
        self.service.update_memory(self.uid, "custom_instructions", "항상 예시를 포함하세요")

        ctx = self.service.build_prompt_context(self.uid)
        self.assertIn("[사용자 메모리]", ctx)
        self.assertIn("AI", ctx)
        self.assertIn("전문적", ctx)
        self.assertIn("예시를 포함", ctx)

    def test_build_prompt_context_feedback(self):
        """피드백 히스토리가 컨텍스트에 포함"""
        self.service.update_memory(self.uid, "feedback_history", "더 간결하게")
        ctx = self.service.build_prompt_context(self.uid)
        self.assertIn("간결", ctx)

    def test_multiple_users(self):
        """사용자별 독립 메모리"""
        self.service.update_memory("user1", "language", "ko")
        self.service.update_memory("user2", "language", "en")

        self.assertEqual(self.service.get_value("user1", "language"), "ko")
        self.assertEqual(self.service.get_value("user2", "language"), "en")


if __name__ == '__main__':
    unittest.main()
