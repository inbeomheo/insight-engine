"""
프롬프트 템플릿 갤러리 통합 테스트

Supabase를 모킹하여 실제 DB 없이 테스트합니다.
패턴: test_routes_smoke.py의 setUp/tearDown 방식 준용
"""
import unittest
from unittest.mock import patch, MagicMock


# =============================================
# 서비스 단위 테스트
# =============================================

class TestPromptTemplateService(unittest.TestCase):
    """prompt_template_service.py 단위 테스트"""

    def _make_row(self, overrides=None):
        """테스트용 DB 행 생성"""
        row = {
            'id': 'test-uuid-1234',
            'user_id': 'user-uuid-abcd',
            'name': '마케팅 분석',
            'description': '마케팅 인사이트 추출',
            'prompt_text': '당신은 마케팅 전문가입니다. 분석해주세요.',
            'style_base': 'blog_seo',
            'is_public': False,
            'usage_count': 5,
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-01T00:00:00Z',
        }
        if overrides:
            row.update(overrides)
        return row

    @patch('services.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_get_templates_supabase_disabled(self, _mock):
        """Supabase 비활성화 시 빈 목록 반환"""
        from services.prompt_template_service import get_templates
        result = get_templates(user_id=None)
        self.assertEqual(result['templates'], [])
        self.assertEqual(result['total'], 0)
        self.assertFalse(result['has_more'])

    @patch('services.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_create_template_supabase_disabled(self, _mock):
        """Supabase 비활성화 시 로컬 템플릿 반환"""
        from services.prompt_template_service import create_template
        result = create_template(
            user_id='user-1',
            data={
                'name': '테스트',
                'prompt_text': '프롬프트 내용',
                'style_base': 'blog_seo',
            }
        )
        self.assertIsNotNone(result)
        self.assertTrue(result['id'].startswith('local_'))
        self.assertEqual(result['name'], '테스트')
        self.assertTrue(result['is_owner'])

    @patch('services.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_delete_template_supabase_disabled(self, _mock):
        """Supabase 비활성화 시 False 반환"""
        from services.prompt_template_service import delete_template
        result = delete_template(template_id='some-id', user_id='user-1')
        self.assertFalse(result)

    def test_format_template_is_owner(self):
        """_format_template: 소유자 여부 올바르게 반환"""
        from services.prompt_template_service import _format_template
        row = self._make_row()
        # 소유자인 경우
        formatted = _format_template(row, viewer_user_id='user-uuid-abcd')
        self.assertTrue(formatted['is_owner'])
        # 타인인 경우
        formatted2 = _format_template(row, viewer_user_id='other-user')
        self.assertFalse(formatted2['is_owner'])
        # 비로그인인 경우
        formatted3 = _format_template(row, viewer_user_id=None)
        self.assertFalse(formatted3['is_owner'])

    def test_format_template_fields(self):
        """_format_template: 필수 필드 포함 확인"""
        from services.prompt_template_service import _format_template
        row = self._make_row()
        result = _format_template(row, viewer_user_id=None)
        required_keys = {'id', 'name', 'description', 'prompt_text', 'style_base',
                         'is_public', 'usage_count', 'created_at', 'updated_at', 'is_owner'}
        self.assertTrue(required_keys.issubset(result.keys()))

    def test_empty_page_structure(self):
        """_empty_page: 빈 페이지 구조 확인"""
        from services.prompt_template_service import _empty_page
        result = _empty_page(page=2)
        self.assertEqual(result['page'], 2)
        self.assertEqual(result['templates'], [])
        self.assertFalse(result['has_more'])

    @patch('services.prompt_template_service.is_supabase_enabled', return_value=True)
    @patch('services.prompt_template_service.get_supabase')
    def test_create_template_success(self, mock_get_supabase, _mock_enabled):
        """Supabase 활성화 시 템플릿 생성"""
        from services.prompt_template_service import create_template

        row = self._make_row()
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        # 개수 조회용 체인 (count_result.count = 0)
        count_chain = MagicMock()
        count_chain.count = 0
        # insert 결과
        insert_result = MagicMock()
        insert_result.data = [row]

        # table().select().eq().execute() → count_result
        # table().insert().execute() → insert_result
        mock_count_table = MagicMock()
        mock_count_table.select.return_value = mock_count_table
        mock_count_table.eq.return_value = mock_count_table
        mock_count_table.execute.return_value = count_chain

        mock_insert_table = MagicMock()
        mock_insert_table.insert.return_value = mock_insert_table
        mock_insert_table.execute.return_value = insert_result

        # 첫 번째 table() 호출 = count 조회, 두 번째 = insert
        mock_sb.table.side_effect = [mock_count_table, mock_insert_table]

        result = create_template(
            user_id='user-uuid-abcd',
            data={'name': '마케팅 분석', 'prompt_text': '분석해주세요.', 'style_base': 'blog_seo'}
        )
        self.assertIsNotNone(result)

    @patch('services.prompt_template_service.is_supabase_enabled', return_value=True)
    @patch('services.prompt_template_service.get_supabase')
    def test_create_template_limit_exceeded(self, mock_get_supabase, _mock_enabled):
        """최대 개수(50개) 초과 시 ValueError 발생 → None 반환"""
        from services.prompt_template_service import create_template, MAX_TEMPLATES_PER_USER

        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        count_chain = MagicMock()
        count_chain.count = MAX_TEMPLATES_PER_USER  # 이미 최대

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = count_chain
        mock_sb.table.return_value = mock_table

        # ValueError 발생 → _db_op가 None 반환
        result = create_template(
            user_id='user-uuid-abcd',
            data={'name': 'test', 'prompt_text': 'test'}
        )
        self.assertIsNone(result)


# =============================================
# API 라우트 통합 테스트
# =============================================

class TestTemplateRoutes(unittest.TestCase):
    """Flask 라우트 통합 테스트"""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    def tearDown(self):
        pass

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_templates_no_auth(self, _mock):
        """GET /api/templates — 비로그인 상태 (Supabase 비활성화)"""
        res = self.client.get('/api/templates')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('templates', data)
        self.assertIn('total', data)
        self.assertIsInstance(data['templates'], list)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.prompt_template_service.is_supabase_enabled', return_value=False)
    def test_create_template_no_auth(self, _mock1, _mock2):
        """POST /api/templates — 비로그인 상태 (Supabase 비활성화)"""
        res = self.client.post('/api/templates', json={
            'name': '테스트 템플릿',
            'prompt_text': '당신은 전문가입니다.',
        })
        # Supabase 비활성화 → 로컬 모드로 201 반환
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn('id', data)
        self.assertEqual(data['name'], '테스트 템플릿')

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_missing_name(self, _mock):
        """POST /api/templates — 이름 누락 시 400"""
        res = self.client.post('/api/templates', json={
            'prompt_text': '프롬프트만 있음',
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('error', data)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_missing_prompt(self, _mock):
        """POST /api/templates — 프롬프트 누락 시 400"""
        res = self.client.post('/api/templates', json={
            'name': '이름만 있음',
        })
        self.assertEqual(res.status_code, 400)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_name_too_long(self, _mock):
        """POST /api/templates — 이름 50자 초과 시 400"""
        res = self.client.post('/api/templates', json={
            'name': 'A' * 51,
            'prompt_text': '프롬프트 내용',
        })
        self.assertEqual(res.status_code, 400)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_prompt_too_long(self, _mock):
        """POST /api/templates — 프롬프트 5000자 초과 시 400"""
        res = self.client.post('/api/templates', json={
            'name': '정상 이름',
            'prompt_text': 'P' * 5001,
        })
        self.assertEqual(res.status_code, 400)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.prompt_template_service.delete_template', return_value=False)
    def test_delete_template_not_found(self, _mock_del, _mock_supabase):
        """DELETE /api/templates/<id> — 없는 템플릿 삭제 시 404"""
        res = self.client.delete('/api/templates/nonexistent-id')
        self.assertEqual(res.status_code, 404)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.prompt_template_service.update_template', return_value=None)
    def test_update_template_not_found(self, _mock_upd, _mock_supabase):
        """PUT /api/templates/<id> — 없는 템플릿 수정 시 404"""
        res = self.client.put('/api/templates/nonexistent-id', json={'name': '새 이름'})
        self.assertEqual(res.status_code, 404)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_templates_search_param(self, _mock):
        """GET /api/templates?search=키워드 — 검색 파라미터 처리"""
        res = self.client.get('/api/templates?search=마케팅&page=1')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('templates', data)
        self.assertEqual(data['page'], 1)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.prompt_template_service.get_template_by_id', return_value=None)
    def test_use_template_not_found(self, _mock_get, _mock_supabase):
        """POST /api/templates/<id>/use — 없는 템플릿 사용 시 404"""
        res = self.client.post('/api/templates/nonexistent-id/use')
        self.assertEqual(res.status_code, 404)


if __name__ == '__main__':
    unittest.main()
