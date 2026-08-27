"""prompt_template_service 단위 테스트"""
import unittest
from unittest.mock import MagicMock, patch

from services.data.prompt_template_service import (
    _format_template,
    _empty_page,
    _local_template,
    _db_op,
    MAX_TEMPLATES_PER_USER,
    PAGE_SIZE,
    get_templates,
    get_template_by_id,
    create_template,
    update_template,
    delete_template,
    increment_usage,
)


class TestConstants(unittest.TestCase):

    def test_max_templates(self):
        """사용자당 최대 템플릿 수"""
        self.assertEqual(MAX_TEMPLATES_PER_USER, 50)

    def test_page_size(self):
        """페이지 크기"""
        self.assertEqual(PAGE_SIZE, 20)


class TestFormatTemplate(unittest.TestCase):

    def test_basic(self):
        """기본 변환"""
        row = {
            'id': 'tpl1',
            'name': '테스트',
            'description': '설명',
            'prompt_text': '프롬프트',
            'style_base': 'blog_seo',
            'is_public': True,
            'usage_count': 5,
            'created_at': '2026-01-01',
            'updated_at': '2026-01-02',
            'user_id': 'user1',
        }
        result = _format_template(row, 'user1')
        self.assertEqual(result['id'], 'tpl1')
        self.assertEqual(result['name'], '테스트')
        self.assertTrue(result['is_owner'])

    def test_not_owner(self):
        """다른 사용자 → is_owner=False"""
        row = {'id': 'tpl1', 'user_id': 'user1'}
        result = _format_template(row, 'user2')
        self.assertFalse(result['is_owner'])

    def test_no_viewer(self):
        """비로그인 → is_owner=False"""
        row = {'id': 'tpl1', 'user_id': 'user1'}
        result = _format_template(row, None)
        self.assertFalse(result['is_owner'])

    def test_defaults(self):
        """빈 row → 기본값"""
        result = _format_template({}, None)
        self.assertEqual(result['name'], '')
        self.assertEqual(result['style_base'], 'blog_seo')
        self.assertEqual(result['usage_count'], 0)
        self.assertFalse(result['is_public'])


class TestEmptyPage(unittest.TestCase):

    def test_structure(self):
        """빈 페이지 구조"""
        result = _empty_page(3)
        self.assertEqual(result['templates'], [])
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['page'], 3)
        self.assertEqual(result['per_page'], PAGE_SIZE)
        self.assertFalse(result['has_more'])


class TestLocalTemplate(unittest.TestCase):

    def test_basic(self):
        """로컬 템플릿 생성"""
        data = {'name': '로컬', 'prompt_text': '프롬프트', 'style_base': 'summary'}
        result = _local_template(data)
        self.assertTrue(result['id'].startswith('local_'))
        self.assertEqual(result['name'], '로컬')
        self.assertEqual(result['prompt_text'], '프롬프트')
        self.assertTrue(result['is_owner'])
        self.assertFalse(result['is_public'])

    def test_defaults(self):
        """기본값"""
        result = _local_template({})
        self.assertEqual(result['style_base'], 'blog_seo')
        self.assertEqual(result['usage_count'], 0)


class TestDbOp(unittest.TestCase):

    def test_success(self):
        """정상 실행"""
        result = _db_op('test', 'default', lambda: 42)
        self.assertEqual(result, 42)

    def test_error_returns_default(self):
        """예외 → 기본값 반환"""
        def fail():
            raise RuntimeError('fail')
        result = _db_op('test', 'fallback', fail)
        self.assertEqual(result, 'fallback')


class TestSupabaseDisabled(unittest.TestCase):

    @patch('services.data.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_get_templates(self, mock_sb):
        """Supabase 비활성 → 빈 페이지"""
        result = get_templates('user1')
        self.assertEqual(result['templates'], [])

    @patch('services.data.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_get_template_by_id(self, mock_sb):
        """Supabase 비활성 → None"""
        self.assertIsNone(get_template_by_id('tpl1', 'user1'))

    @patch('services.data.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_create_template_local(self, mock_sb):
        """Supabase 비활성 → 로컬 템플릿"""
        result = create_template('user1', {'name': 'test', 'prompt_text': 'p'})
        self.assertTrue(result['id'].startswith('local_'))

    @patch('services.data.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_update_template(self, mock_sb):
        """Supabase 비활성 → None"""
        self.assertIsNone(update_template('tpl1', 'user1', {'name': 'new'}))

    @patch('services.data.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_delete_template(self, mock_sb):
        """Supabase 비활성 → False"""
        self.assertFalse(delete_template('tpl1', 'user1'))

    @patch('services.data.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_increment_usage(self, mock_sb):
        """Supabase 비활성 → False"""
        self.assertFalse(increment_usage('tpl1'))


class TestTemplateUsageAccounting(unittest.TestCase):

    @patch('services.data.prompt_template_service.is_supabase_enabled', return_value=True)
    @patch('services.data.prompt_template_service.get_service_supabase')
    def test_increment_usage_uses_server_only_client(self, service_client, _enabled):
        client = MagicMock()
        service_client.return_value = client

        self.assertTrue(increment_usage('tpl1'))

        client.rpc.assert_called_once_with(
            'increment_template_usage',
            {'p_template_id': 'tpl1'},
        )


if __name__ == '__main__':
    unittest.main()
