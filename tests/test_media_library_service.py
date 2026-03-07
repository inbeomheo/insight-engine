"""media_library_service 단위 테스트"""
import unittest

from services import media_library_service


class TestMediaLibraryService(unittest.TestCase):

    def setUp(self):
        with media_library_service._lock:
            media_library_service._media.clear()

    def test_register_media(self):
        """미디어 등록"""
        item = media_library_service.register_media('test.png', 'https://cdn/test.png', 'image', 1024)
        self.assertIn('id', item)
        self.assertEqual(item['name'], 'test.png')
        self.assertEqual(item['media_type'], 'image')
        self.assertEqual(item['size_bytes'], 1024)

    def test_register_invalid_type_fallback(self):
        """잘못된 타입 → 'other'로 폴백"""
        item = media_library_service.register_media('file.xyz', 'url', 'unknown_type')
        self.assertEqual(item['media_type'], 'other')

    def test_get_media(self):
        """미디어 조회"""
        item = media_library_service.register_media('img.jpg', 'url')
        fetched = media_library_service.get_media(item['id'])
        self.assertEqual(fetched['name'], 'img.jpg')

    def test_get_deleted_returns_none(self):
        """삭제된 미디어 조회 → None"""
        item = media_library_service.register_media('del.png', 'url')
        media_library_service.delete_media(item['id'])
        self.assertIsNone(media_library_service.get_media(item['id']))

    def test_get_nonexistent_returns_none(self):
        """없는 미디어 조회 → None"""
        self.assertIsNone(media_library_service.get_media('bad-id'))

    def test_list_media_filter_by_type(self):
        """타입별 필터링"""
        media_library_service.register_media('a.png', 'url', 'image')
        media_library_service.register_media('b.mp4', 'url', 'video')
        result = media_library_service.list_media(media_type='image')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['items'][0]['media_type'], 'image')

    def test_list_media_filter_by_workspace(self):
        """워크스페이스별 필터링"""
        media_library_service.register_media('a.png', 'url', workspace_id='ws1')
        media_library_service.register_media('b.png', 'url', workspace_id='ws2')
        result = media_library_service.list_media(workspace_id='ws1')
        self.assertEqual(result['total'], 1)

    def test_list_media_search_query(self):
        """이름 검색"""
        media_library_service.register_media('파이썬 로고', 'url')
        media_library_service.register_media('자바 로고', 'url')
        result = media_library_service.list_media(query='파이썬')
        self.assertEqual(result['total'], 1)

    def test_list_media_pagination(self):
        """페이지네이션"""
        for i in range(5):
            media_library_service.register_media(f'img{i}.png', 'url')
        result = media_library_service.list_media(page=1, per_page=2)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual(result['total'], 5)

    def test_delete_soft(self):
        """소프트 삭제"""
        item = media_library_service.register_media('del.png', 'url')
        self.assertTrue(media_library_service.delete_media(item['id'], soft=True))
        self.assertIsNone(media_library_service.get_media(item['id']))

    def test_delete_hard(self):
        """하드 삭제"""
        item = media_library_service.register_media('hard.png', 'url')
        self.assertTrue(media_library_service.delete_media(item['id'], soft=False))
        self.assertIsNone(media_library_service.get_media(item['id']))

    def test_delete_nonexistent(self):
        """없는 미디어 삭제 → False"""
        self.assertFalse(media_library_service.delete_media('bad'))

    def test_update_media(self):
        """미디어 업데이트"""
        item = media_library_service.register_media('old.png', 'url')
        updated = media_library_service.update_media(item['id'], name='new.png')
        self.assertEqual(updated['name'], 'new.png')

    def test_update_nonexistent(self):
        """없는 미디어 업데이트 → None"""
        self.assertIsNone(media_library_service.update_media('bad', name='x'))

    def test_storage_stats(self):
        """스토리지 통계"""
        media_library_service.register_media('a.png', 'url', 'image', size_bytes=100)
        media_library_service.register_media('b.mp4', 'url', 'video', size_bytes=200)
        stats = media_library_service.get_storage_stats()
        self.assertEqual(stats['total_items'], 2)
        self.assertEqual(stats['total_size_bytes'], 300)
        self.assertEqual(stats['by_type']['image'], 1)

    def test_list_media_filter_by_tags(self):
        """태그 필터링"""
        media_library_service.register_media('a.png', 'url', tags=['logo', 'python'])
        media_library_service.register_media('b.png', 'url', tags=['logo', 'java'])
        result = media_library_service.list_media(tags=['logo', 'python'])
        self.assertEqual(result['total'], 1)


if __name__ == '__main__':
    unittest.main()
