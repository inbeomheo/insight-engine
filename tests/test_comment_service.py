"""comment_service 단위 테스트"""
import unittest

from services.content import comment_service


class TestCommentService(unittest.TestCase):
    """댓글 서비스 테스트"""

    def setUp(self):
        with comment_service._lock:
            comment_service._comments.clear()

    def test_add_comment(self):
        """댓글 추가"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '좋은 글이네요')
        self.assertIn('id', c)
        self.assertEqual(c['item_id'], 'item1')
        self.assertFalse(c['is_resolved'])

    def test_mention_extraction(self):
        """@멘션 추출"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '@bob 확인 부탁 @charlie')
        self.assertEqual(c['mentions'], ['bob', 'charlie'])

    def test_get_comment(self):
        """댓글 조회"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '내용')
        found = comment_service.get_comment(c['id'])
        self.assertIsNotNone(found)

    def test_get_deleted_comment(self):
        """삭제된 댓글 조회 시 None"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '내용')
        comment_service.delete_comment(c['id'], 'u1')
        self.assertIsNone(comment_service.get_comment(c['id']))

    def test_update_comment(self):
        """댓글 수정"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '원본')
        updated = comment_service.update_comment(c['id'], 'u1', '수정됨')
        self.assertEqual(updated['text'], '수정됨')

    def test_update_wrong_user(self):
        """다른 사용자 수정 불가"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '원본')
        self.assertIsNone(comment_service.update_comment(c['id'], 'u2', '수정'))

    def test_delete_comment(self):
        """댓글 삭제"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '내용')
        self.assertTrue(comment_service.delete_comment(c['id'], 'u1'))

    def test_delete_wrong_user(self):
        """다른 사용자 삭제 불가"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '내용')
        self.assertFalse(comment_service.delete_comment(c['id'], 'u2'))

    def test_resolve_comment(self):
        """댓글 해결 처리"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '수정 필요')
        resolved = comment_service.resolve_comment(c['id'], 'u2')
        self.assertTrue(resolved['is_resolved'])
        self.assertEqual(resolved['resolved_by'], 'u2')

    def test_add_reaction_toggle(self):
        """이모지 반응 추가/토글"""
        c = comment_service.add_comment('item1', 'u1', 'Alice', '내용')
        comment_service.add_reaction(c['id'], 'u2', '👍')
        self.assertIn('u2', c['reactions']['👍'])
        comment_service.add_reaction(c['id'], 'u2', '👍')
        self.assertNotIn('u2', c['reactions']['👍'])

    def test_list_comments(self):
        """댓글 목록"""
        comment_service.add_comment('item1', 'u1', 'A', '댓글1')
        comment_service.add_comment('item1', 'u2', 'B', '댓글2')
        comment_service.add_comment('item2', 'u1', 'A', '다른 아이템')
        result = comment_service.list_comments('item1')
        self.assertEqual(len(result), 2)

    def test_list_exclude_resolved(self):
        """해결된 댓글 제외"""
        c = comment_service.add_comment('item1', 'u1', 'A', '댓글')
        comment_service.resolve_comment(c['id'], 'u1')
        result = comment_service.list_comments('item1', include_resolved=False)
        self.assertEqual(len(result), 0)

    def test_get_mentions(self):
        """멘션된 댓글 목록"""
        comment_service.add_comment('item1', 'u1', 'A', '@bob 확인')
        result = comment_service.get_mentions('bob')
        self.assertEqual(len(result), 1)


if __name__ == '__main__':
    unittest.main()
