"""prompt_version_service 단위 테스트"""
import os
import shutil
import tempfile
import unittest

from services.prompt_version_service import PromptVersionService, PromptVersion


class TestPromptVersion(unittest.TestCase):

    def test_make_version_id(self):
        """버전 ID 생성 (SHA256 16자)"""
        vid = PromptVersion.make_version_id('test content')
        self.assertEqual(len(vid), 16)
        # 동일 입력 → 동일 출력
        self.assertEqual(vid, PromptVersion.make_version_id('test content'))

    def test_different_content_different_id(self):
        """다른 콘텐츠 → 다른 ID"""
        v1 = PromptVersion.make_version_id('aaa')
        v2 = PromptVersion.make_version_id('bbb')
        self.assertNotEqual(v1, v2)


class TestPromptVersionService(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store_path = os.path.join(self.tmpdir, 'versions.jsonl')
        self.svc = PromptVersionService(store_path=self.store_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_version(self):
        """버전 저장"""
        v = self.svc.save_version('blog_seo', '프롬프트 내용 v1', description='초기')
        self.assertEqual(v.prompt_key, 'blog_seo')
        self.assertEqual(v.version_num, 1)
        self.assertTrue(v.is_active)

    def test_save_multiple_versions(self):
        """여러 버전 저장 시 마지막만 활성"""
        self.svc.save_version('key', 'v1')
        v2 = self.svc.save_version('key', 'v2')
        history = self.svc.get_history('key')
        active_count = sum(1 for v in history if v.is_active)
        self.assertEqual(active_count, 1)
        self.assertTrue(v2.is_active)

    def test_get_active(self):
        """활성 버전 조회"""
        self.svc.save_version('key', 'v1')
        self.svc.save_version('key', 'v2')
        active = self.svc.get_active('key')
        self.assertEqual(active.version_num, 2)

    def test_get_active_empty(self):
        """버전 없을 때 → None"""
        self.assertIsNone(self.svc.get_active('nonexistent'))

    def test_get_by_version_num(self):
        """버전 번호로 조회"""
        self.svc.save_version('key', 'v1')
        self.svc.save_version('key', 'v2')
        v = self.svc.get_by_version_num('key', 1)
        self.assertEqual(v.content, 'v1')

    def test_get_by_version_num_nonexistent(self):
        """없는 버전 번호 → None"""
        self.assertIsNone(self.svc.get_by_version_num('key', 99))

    def test_rollback(self):
        """롤백"""
        self.svc.save_version('key', 'v1')
        self.svc.save_version('key', 'v2')
        rolled = self.svc.rollback('key', 1)
        self.assertIsNotNone(rolled)
        self.assertTrue(rolled.is_active)
        active = self.svc.get_active('key')
        self.assertEqual(active.version_num, 1)

    def test_rollback_nonexistent(self):
        """없는 버전으로 롤백 → None"""
        self.assertIsNone(self.svc.rollback('key', 99))

    def test_record_metric(self):
        """메트릭 기록"""
        v = self.svc.save_version('key', 'content')
        self.svc.record_metric('key', v.version_id, 'quality', 0.95)
        updated = self.svc.get_active('key')
        self.assertEqual(updated.metrics['quality'], 0.95)

    def test_diff(self):
        """버전 diff"""
        self.svc.save_version('key', '라인1\n라인2\n라인3')
        self.svc.save_version('key', '라인1\n변경됨\n라인3')
        d = self.svc.diff('key', 1, 2)
        self.assertIn('라인2', d['removed_lines'])
        self.assertIn('변경됨', d['added_lines'])

    def test_diff_nonexistent(self):
        """없는 버전 diff → error"""
        d = self.svc.diff('key', 1, 2)
        self.assertIn('error', d)

    def test_get_history(self):
        """이력 조회"""
        self.svc.save_version('key', 'v1')
        self.svc.save_version('key', 'v2')
        history = self.svc.get_history('key')
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].version_num, 1)

    def test_persistence(self):
        """파일 저장 후 새 인스턴스에서 읽기"""
        self.svc.save_version('key', 'persisted')
        svc2 = PromptVersionService(store_path=self.store_path)
        history = svc2.get_history('key')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].content, 'persisted')


if __name__ == '__main__':
    unittest.main()
