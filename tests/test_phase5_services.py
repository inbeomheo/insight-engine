"""Phase 5 Group A 백엔드 서비스 단위 테스트"""
import unittest


class TestVersionService(unittest.TestCase):
    """버전 히스토리 서비스 테스트 (F5-04)"""

    def setUp(self):
        from services import version_service
        version_service._versions.clear()

    def test_save_and_list_versions(self):
        from services.data.version_service import save_version, list_versions
        v1 = save_version('c1', '제목1', '내용1')
        v2 = save_version('c1', '제목2', '내용2')

        versions = list_versions('c1')
        self.assertEqual(len(versions), 2)
        # 최신순 정렬
        self.assertEqual(versions[0]['version'], 2)
        self.assertEqual(versions[1]['version'], 1)

    def test_get_version(self):
        from services.data.version_service import save_version, get_version
        v = save_version('c1', '제목', '내용', html='<p>내용</p>')
        result = get_version('c1', v['id'])
        self.assertIsNotNone(result)
        self.assertEqual(result['content'], '내용')
        self.assertEqual(result['html'], '<p>내용</p>')

    def test_get_version_not_found(self):
        from services.data.version_service import get_version
        self.assertIsNone(get_version('c1', 'nonexistent'))

    def test_diff_versions(self):
        from services.data.version_service import save_version, diff_versions
        v1 = save_version('c1', '제목', '라인1\n라인2')
        v2 = save_version('c1', '제목', '라인1\n라인3')

        result = diff_versions('c1', v1['id'], v2['id'])
        self.assertIsNotNone(result)
        self.assertIn('diff', result)
        self.assertGreater(result['additions'], 0)

    def test_restore_version(self):
        from services.data.version_service import save_version, restore_version, list_versions
        v1 = save_version('c1', '제목', '원본 내용')
        save_version('c1', '제목', '수정된 내용')

        restored = restore_version('c1', v1['id'])
        self.assertIsNotNone(restored)
        self.assertEqual(restored['content'], '원본 내용')
        self.assertIn('복원됨', restored['note'])

        versions = list_versions('c1')
        self.assertEqual(len(versions), 3)

    def test_max_versions_limit(self):
        from services.data.version_service import save_version, list_versions, MAX_VERSIONS_PER_CONTENT
        for i in range(MAX_VERSIONS_PER_CONTENT + 10):
            save_version('c1', f'제목{i}', f'내용{i}')

        from services.data.version_service import _versions
        self.assertLessEqual(len(_versions['c1']), MAX_VERSIONS_PER_CONTENT)


class TestSearchService(unittest.TestCase):
    """전문 검색 서비스 테스트 (F5-09)"""

    def setUp(self):
        from services import search_service
        search_service._index.clear()

    def test_index_and_search(self):
        from services.seo.search_service import index_content, search
        index_content('1', 'Python 튜토리얼', 'Python 기초 문법을 배웁니다')
        index_content('2', 'JavaScript 가이드', 'JS 기초를 배웁니다')

        result = search('Python')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['results'][0]['id'], '1')

    def test_empty_query(self):
        from services.seo.search_service import search
        result = search('')
        self.assertEqual(result['total'], 0)

    def test_and_matching(self):
        from services.seo.search_service import index_content, search
        index_content('1', 'Python 기초', 'Python 문법 기초 가이드')
        index_content('2', 'Python 고급', 'Python 데코레이터 패턴')

        result = search('Python 기초')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['results'][0]['id'], '1')

    def test_style_filter(self):
        from services.seo.search_service import index_content, search
        index_content('1', '제목1', '내용', style='blog_seo')
        index_content('2', '제목2', '내용', style='summary')

        result = search('내용', style_filter='blog_seo')
        self.assertEqual(result['total'], 1)

    def test_title_weight(self):
        from services.seo.search_service import index_content, search
        index_content('1', 'AI 관련 없는 제목', 'React 기초')
        index_content('2', 'React 튜토리얼', 'AI 관련 내용')

        result = search('React')
        self.assertEqual(len(result['results']), 2)
        # 제목에 매칭되는 결과가 먼저 나옴
        self.assertEqual(result['results'][0]['id'], '2')


class TestFolderService(unittest.TestCase):
    """폴더/카테고리 서비스 테스트 (F5-11)"""

    def setUp(self):
        from services import folder_service
        folder_service._folders.clear()
        folder_service._content_folders.clear()

    def test_create_and_list_folders(self):
        from services.data.folder_service import create_folder, list_folders
        create_folder('기술')
        create_folder('마케팅')

        folders = list_folders()
        self.assertEqual(len(folders), 2)

    def test_delete_folder(self):
        from services.data.folder_service import create_folder, delete_folder, list_folders
        f = create_folder('삭제용')
        self.assertTrue(delete_folder(f['id']))
        self.assertEqual(len(list_folders()), 0)

    def test_delete_nonexistent(self):
        from services.data.folder_service import delete_folder
        self.assertFalse(delete_folder('nonexistent'))

    def test_move_content(self):
        from services.data.folder_service import create_folder, move_content, get_content_folder, list_folder_contents
        f = create_folder('폴더1')
        self.assertTrue(move_content('c1', f['id']))
        self.assertEqual(get_content_folder('c1'), f['id'])
        self.assertIn('c1', list_folder_contents(f['id']))

    def test_move_to_uncategorized(self):
        from services.data.folder_service import create_folder, move_content, get_content_folder
        f = create_folder('폴더1')
        move_content('c1', f['id'])
        move_content('c1', None)
        self.assertIsNone(get_content_folder('c1'))

    def test_update_folder(self):
        from services.data.folder_service import create_folder, update_folder
        f = create_folder('원래이름')
        updated = update_folder(f['id'], name='새이름')
        self.assertEqual(updated['name'], '새이름')


class TestNotificationService(unittest.TestCase):
    """알림 센터 서비스 테스트 (F5-13)"""

    def setUp(self):
        from services import notification_service
        notification_service._notifications.clear()

    def test_create_and_list(self):
        from services.data.notification_service import create_notification, list_notifications
        create_notification('user1', 'system', '테스트', '메시지1')
        create_notification('user1', 'system', '테스트2', '메시지2')

        result = list_notifications('user1')
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['unread_count'], 2)

    def test_mark_read(self):
        from services.data.notification_service import create_notification, mark_read, list_notifications
        n = create_notification('user1', 'system', '테스트', '메시지')
        self.assertTrue(mark_read('user1', n['id']))

        result = list_notifications('user1')
        self.assertEqual(result['unread_count'], 0)

    def test_mark_all_read(self):
        from services.data.notification_service import create_notification, mark_all_read, get_unread_count
        create_notification('user1', 'system', '1', 'msg')
        create_notification('user1', 'system', '2', 'msg')

        count = mark_all_read('user1')
        self.assertEqual(count, 2)
        self.assertEqual(get_unread_count('user1'), 0)

    def test_delete_notification(self):
        from services.data.notification_service import create_notification, delete_notification, list_notifications
        n = create_notification('user1', 'system', '테스트', '메시지')
        self.assertTrue(delete_notification('user1', n['id']))
        self.assertEqual(list_notifications('user1')['total'], 0)

    def test_unread_filter(self):
        from services.data.notification_service import create_notification, mark_read, list_notifications
        n1 = create_notification('user1', 'system', '1', 'msg')
        create_notification('user1', 'system', '2', 'msg')
        mark_read('user1', n1['id'])

        result = list_notifications('user1', unread_only=True)
        self.assertEqual(result['total'], 1)

    def test_max_notifications(self):
        from services.data.notification_service import create_notification, MAX_NOTIFICATIONS_PER_USER
        from services import notification_service
        for i in range(MAX_NOTIFICATIONS_PER_USER + 10):
            create_notification('user1', 'system', f'알림{i}', f'메시지{i}')

        self.assertLessEqual(len(notification_service._notifications['user1']),
                             MAX_NOTIFICATIONS_PER_USER)


class TestCollaborationService(unittest.TestCase):
    """협업 서비스 테스트 (F5-02)"""

    def setUp(self):
        from services import collaboration_service
        collaboration_service._sessions.clear()

    def test_create_session(self):
        from services.data.collaboration_service import create_session
        result = create_session('c1', 'user1', 'Alice')
        self.assertIn('session_id', result)
        self.assertEqual(len(result['participants']), 1)

    def test_join_existing_session(self):
        from services.data.collaboration_service import create_session
        r1 = create_session('c1', 'user1', 'Alice')
        r2 = create_session('c1', 'user2', 'Bob')
        self.assertEqual(r1['session_id'], r2['session_id'])
        self.assertEqual(len(r2['participants']), 2)

    def test_update_content(self):
        from services.data.collaboration_service import create_session, update_content
        r = create_session('c1', 'user1')
        result = update_content(r['session_id'], 'user1', '새 내용', 3)
        self.assertIsNotNone(result)
        self.assertEqual(result['version'], 1)

    def test_leave_session(self):
        from services.data.collaboration_service import create_session, leave_session, get_session
        r = create_session('c1', 'user1')
        leave_session(r['session_id'], 'user1')
        # 참가자 없으면 세션 자동 삭제
        self.assertIsNone(get_session(r['session_id']))

    def test_heartbeat(self):
        from services.data.collaboration_service import create_session, heartbeat
        r = create_session('c1', 'user1')
        self.assertTrue(heartbeat(r['session_id'], 'user1', 10))
        self.assertFalse(heartbeat(r['session_id'], 'nonexistent'))


if __name__ == '__main__':
    unittest.main()
