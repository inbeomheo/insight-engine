"""version_service 단위 테스트"""
import unittest

from services import version_service


class TestVersionService(unittest.TestCase):
    """버전 히스토리 서비스 테스트"""

    def setUp(self):
        version_service._versions.clear()

    def test_save_version(self):
        """버전 저장"""
        v = version_service.save_version('c1', '제목', '본문 v1')
        self.assertEqual(v['content_id'], 'c1')
        self.assertEqual(v['version'], 1)

    def test_incremental_version_number(self):
        """버전 번호 자동 증가"""
        version_service.save_version('c1', '제목', 'v1')
        v2 = version_service.save_version('c1', '제목', 'v2')
        self.assertEqual(v2['version'], 2)

    def test_list_versions_newest_first(self):
        """버전 목록 최신순 반환"""
        version_service.save_version('c1', '제목', 'v1')
        version_service.save_version('c1', '제목', 'v2')
        versions = version_service.list_versions('c1')
        self.assertEqual(versions[0]['version'], 2)

    def test_list_versions_excludes_content(self):
        """목록에서 content/html 필드 제외"""
        version_service.save_version('c1', '제목', '본문')
        versions = version_service.list_versions('c1')
        self.assertNotIn('content', versions[0])
        self.assertNotIn('html', versions[0])

    def test_get_version(self):
        """특정 버전 조회"""
        v = version_service.save_version('c1', '제목', '본문')
        found = version_service.get_version('c1', v['id'])
        self.assertEqual(found['content'], '본문')

    def test_get_version_not_found(self):
        """없는 버전 조회 시 None"""
        self.assertIsNone(version_service.get_version('c1', 'no-id'))

    def test_diff_versions(self):
        """두 버전 diff"""
        v1 = version_service.save_version('c1', '제목', '라인1\n라인2')
        v2 = version_service.save_version('c1', '제목', '라인1\n라인2 수정\n라인3')
        diff = version_service.diff_versions('c1', v1['id'], v2['id'])
        self.assertIsNotNone(diff)
        self.assertGreater(diff['additions'], 0)

    def test_diff_nonexistent(self):
        """없는 버전 diff 시 None"""
        v1 = version_service.save_version('c1', '제목', '내용')
        self.assertIsNone(version_service.diff_versions('c1', v1['id'], 'no-id'))

    def test_restore_version(self):
        """버전 복원 → 새 버전 생성"""
        v1 = version_service.save_version('c1', '제목', '원본')
        version_service.save_version('c1', '제목', '수정본')
        restored = version_service.restore_version('c1', v1['id'])
        self.assertEqual(restored['version'], 3)
        self.assertEqual(restored['content'], '원본')
        self.assertIn('복원', restored['note'])

    def test_max_versions_limit(self):
        """최대 버전 수 초과 시 오래된 것 제거"""
        original_max = version_service.MAX_VERSIONS_PER_CONTENT
        version_service.MAX_VERSIONS_PER_CONTENT = 5
        try:
            for i in range(8):
                version_service.save_version('c1', '제목', f'v{i}')
            versions = version_service.list_versions('c1')
            self.assertEqual(len(versions), 5)
        finally:
            version_service.MAX_VERSIONS_PER_CONTENT = original_max


if __name__ == '__main__':
    unittest.main()
