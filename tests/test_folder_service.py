"""folder_service 단위 테스트"""
import unittest

from services import folder_service


class TestFolderService(unittest.TestCase):
    """폴더 서비스 테스트"""

    def setUp(self):
        folder_service._folders.clear()
        folder_service._content_folders.clear()

    def test_create_folder(self):
        """폴더 생성"""
        f = folder_service.create_folder('블로그', user_id='u1')
        self.assertEqual(f['name'], '블로그')
        self.assertIn('id', f)

    def test_list_folders_root(self):
        """루트 폴더 목록"""
        folder_service.create_folder('A', user_id='u1')
        folder_service.create_folder('B', user_id='u1')
        result = folder_service.list_folders(parent_id=None)
        self.assertEqual(len(result), 2)

    def test_list_folders_by_user(self):
        """사용자별 폴더 필터링"""
        folder_service.create_folder('A', user_id='u1')
        folder_service.create_folder('B', user_id='u2')
        result = folder_service.list_folders(user_id='u1')
        self.assertEqual(len(result), 1)

    def test_get_folder(self):
        """폴더 조회"""
        f = folder_service.create_folder('조회용')
        self.assertEqual(folder_service.get_folder(f['id'])['name'], '조회용')

    def test_get_folder_not_found(self):
        """없는 폴더 조회 시 None"""
        self.assertIsNone(folder_service.get_folder('no-id'))

    def test_update_folder_name(self):
        """폴더 이름 수정"""
        f = folder_service.create_folder('원래이름')
        updated = folder_service.update_folder(f['id'], name='새이름')
        self.assertEqual(updated['name'], '새이름')

    def test_update_nonexistent(self):
        """없는 폴더 수정 시 None"""
        self.assertIsNone(folder_service.update_folder('no-id', name='x'))

    def test_delete_folder(self):
        """폴더 삭제"""
        f = folder_service.create_folder('삭제용')
        self.assertTrue(folder_service.delete_folder(f['id']))
        self.assertIsNone(folder_service.get_folder(f['id']))

    def test_delete_folder_clears_content(self):
        """폴더 삭제 시 콘텐츠 미분류 이동"""
        f = folder_service.create_folder('폴더')
        folder_service.move_content('c1', f['id'])
        folder_service.delete_folder(f['id'])
        self.assertIsNone(folder_service.get_content_folder('c1'))

    def test_move_content(self):
        """콘텐츠 폴더 이동"""
        f = folder_service.create_folder('대상')
        self.assertTrue(folder_service.move_content('c1', f['id']))
        self.assertEqual(folder_service.get_content_folder('c1'), f['id'])

    def test_move_content_to_none(self):
        """미분류로 이동"""
        f = folder_service.create_folder('폴더')
        folder_service.move_content('c1', f['id'])
        folder_service.move_content('c1', None)
        self.assertIsNone(folder_service.get_content_folder('c1'))

    def test_list_folder_contents(self):
        """폴더 내 콘텐츠 목록"""
        f = folder_service.create_folder('폴더')
        folder_service.move_content('c1', f['id'])
        folder_service.move_content('c2', f['id'])
        contents = folder_service.list_folder_contents(f['id'])
        self.assertEqual(len(contents), 2)


if __name__ == '__main__':
    unittest.main()
