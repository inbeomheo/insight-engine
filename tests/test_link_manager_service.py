"""link_manager_service 단위 테스트"""
import unittest

from services.seo import link_manager_service


class TestLinkManagerService(unittest.TestCase):
    """링크 관리 서비스 테스트"""

    def setUp(self):
        """각 테스트 전 저장소 초기화"""
        with link_manager_service._lock:
            link_manager_service._links.clear()

    def test_add_link(self):
        """링크 추가 성공"""
        link = link_manager_service.add_link('src1', 'target1', label='참조')
        self.assertEqual(link['source_id'], 'src1')
        self.assertEqual(link['target'], 'target1')
        self.assertEqual(link['link_type'], 'internal')
        self.assertFalse(link['is_broken'])

    def test_add_external_link(self):
        """외부 링크 추가"""
        link = link_manager_service.add_link('src1', 'https://example.com', link_type='external')
        self.assertEqual(link['link_type'], 'external')

    def test_remove_link(self):
        """링크 삭제"""
        link = link_manager_service.add_link('src1', 'target1')
        self.assertTrue(link_manager_service.remove_link(link['id']))

    def test_remove_nonexistent_link(self):
        """없는 링크 삭제 시 False"""
        self.assertFalse(link_manager_service.remove_link('no-such-id'))

    def test_get_links_from(self):
        """특정 콘텐츠에서 나가는 링크 조회"""
        link_manager_service.add_link('src1', 'target1')
        link_manager_service.add_link('src1', 'target2')
        link_manager_service.add_link('src2', 'target3')
        links = link_manager_service.get_links_from('src1')
        self.assertEqual(len(links), 2)

    def test_get_backlinks(self):
        """역링크(backlink) 조회"""
        link_manager_service.add_link('src1', 'target1', link_type='internal')
        link_manager_service.add_link('src2', 'target1', link_type='internal')
        link_manager_service.add_link('src3', 'target1', link_type='external')  # 외부는 제외
        backlinks = link_manager_service.get_backlinks('target1')
        self.assertEqual(len(backlinks), 2)

    def test_mark_broken(self):
        """깨진 링크 표시"""
        link = link_manager_service.add_link('src1', 'https://dead.link', link_type='external')
        updated = link_manager_service.mark_broken(link['id'], True)
        self.assertTrue(updated['is_broken'])
        self.assertIsNotNone(updated['last_checked'])

    def test_mark_broken_nonexistent(self):
        """없는 링크에 broken 표시 시 None"""
        self.assertIsNone(link_manager_service.mark_broken('no-such-id'))

    def test_get_broken_links(self):
        """깨진 링크 목록 조회"""
        link1 = link_manager_service.add_link('src1', 'url1')
        link2 = link_manager_service.add_link('src1', 'url2')
        link_manager_service.mark_broken(link1['id'], True)
        broken = link_manager_service.get_broken_links()
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0]['id'], link1['id'])

    def test_get_broken_links_filter_by_source(self):
        """소스별 깨진 링크 필터링"""
        link1 = link_manager_service.add_link('src1', 'url1')
        link2 = link_manager_service.add_link('src2', 'url2')
        link_manager_service.mark_broken(link1['id'], True)
        link_manager_service.mark_broken(link2['id'], True)
        broken = link_manager_service.get_broken_links(source_id='src1')
        self.assertEqual(len(broken), 1)

    def test_get_link(self):
        """링크 단일 조회"""
        link = link_manager_service.add_link('src1', 'target1')
        found = link_manager_service.get_link(link['id'])
        self.assertEqual(found['source_id'], 'src1')

    def test_get_link_not_found(self):
        """없는 링크 조회 시 None"""
        self.assertIsNone(link_manager_service.get_link('no-such-id'))


if __name__ == '__main__':
    unittest.main()
