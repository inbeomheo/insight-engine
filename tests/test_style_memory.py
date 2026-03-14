"""
Personal Style Memory 서비스 통합 테스트
Supabase disabled 환경에서 실행됩니다.
"""
import importlib
import sys
import unittest
from unittest.mock import patch, MagicMock


def _fresh_import():
    """모듈 캐시 문제 방지를 위해 style_memory_service를 신선하게 import합니다."""
    if 'services.data.style_memory_service' in sys.modules:
        del sys.modules['services.data.style_memory_service']
    import services.data.style_memory_service as m
    return m


class TestStyleMemoryService(unittest.TestCase):
    """style_memory_service 단위 테스트"""

    def test_get_profile_supabase_disabled_returns_default(self):
        """Supabase 비활성화 시 기본 프로필 반환"""
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False), \
             patch('services.data.supabase_service.get_supabase', return_value=None):
            m = _fresh_import()
            profile = m.get_profile('user-123')

        self.assertEqual(profile['preferred_length'], 'medium')
        self.assertEqual(profile['preferred_writing_style'], 'conversational')
        self.assertEqual(profile['preferred_styles'], [])
        self.assertEqual(profile['avoid_keywords'], [])
        self.assertTrue(profile['style_memory_enabled'])
        self.assertEqual(profile['generation_count'], 0)

    def test_get_profile_no_supabase_client_returns_default(self):
        """Supabase 활성화지만 클라이언트 없을 때 기본 프로필 반환"""
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service.get_supabase', return_value=None):
            m = _fresh_import()
            profile = m.get_profile('user-123')

        self.assertIn('preferred_length', profile)

    def test_get_profile_supabase_no_row_returns_default(self):
        """Supabase에 프로필 행이 없으면 기본값 반환"""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service.get_supabase', return_value=mock_supabase):
            m = _fresh_import()
            profile = m.get_profile('user-123')

        self.assertEqual(profile['preferred_length'], 'medium')

    def test_get_profile_supabase_with_row(self):
        """Supabase 프로필 행이 있을 때 값 반환"""
        mock_row = {
            'preferred_styles': [{'style_id': 'blog_seo', 'count': 5}],
            'preferred_length': 'long',
            'preferred_writing_style': 'expert',
            'tone_keywords': ['전문적'],
            'avoid_keywords': ['혁신적'],
            'custom_instructions': '항상 결론 먼저',
            'style_memory_enabled': True,
            'generation_count': 10,
        }
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [mock_row]

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service.get_supabase', return_value=mock_supabase):
            m = _fresh_import()
            profile = m.get_profile('user-123')

        self.assertEqual(profile['preferred_length'], 'long')
        self.assertEqual(profile['preferred_writing_style'], 'expert')
        self.assertEqual(profile['avoid_keywords'], ['혁신적'])
        self.assertEqual(profile['generation_count'], 10)

    def test_update_profile_supabase_disabled_noop(self):
        """Supabase 비활성화 시 update_profile은 아무 것도 하지 않음"""
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False), \
             patch('services.data.supabase_service.get_supabase', return_value=None):
            m = _fresh_import()
            # 예외 없이 실행되어야 함
            m.update_profile('user-123', {'style': 'blog_seo', 'modifiers': {'length': 'medium'}})

    def test_update_profile_creates_new_row(self):
        """프로필이 없을 때 신규 행 생성"""
        mock_supabase = MagicMock()
        # 기존 행 없음
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service.get_supabase', return_value=mock_supabase):
            m = _fresh_import()
            m.update_profile('user-123', {'style': 'summary', 'modifiers': {'length': 'short', 'writing_style': 'casual'}})

        # insert가 호출되었는지 확인
        mock_supabase.table.return_value.insert.assert_called_once()
        insert_data = mock_supabase.table.return_value.insert.call_args[0][0]
        self.assertEqual(insert_data['user_id'], 'user-123')
        self.assertEqual(insert_data['preferred_length'], 'short')
        self.assertEqual(insert_data['generation_count'], 1)

    def test_update_profile_updates_existing_row(self):
        """기존 프로필 행이 있을 때 카운트 증가"""
        existing_row = {
            'preferred_styles': [{'style_id': 'blog_seo', 'count': 3}],
            'generation_count': 3,
            'preferred_length': 'medium',
        }
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [existing_row]

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service.get_supabase', return_value=mock_supabase):
            m = _fresh_import()
            m.update_profile('user-123', {'style': 'blog_seo', 'modifiers': {}})

        mock_supabase.table.return_value.update.assert_called_once()
        update_data = mock_supabase.table.return_value.update.call_args[0][0]
        # generation_count가 4로 증가
        self.assertEqual(update_data['generation_count'], 4)

    def test_reset_profile_supabase_disabled_returns_false(self):
        """Supabase 비활성화 시 reset_profile은 False 반환"""
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False), \
             patch('services.data.supabase_service.get_supabase', return_value=None):
            m = _fresh_import()
            result = m.reset_profile('user-123')

        self.assertFalse(result)

    def test_reset_profile_calls_upsert(self):
        """reset_profile은 기본값으로 upsert 호출"""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = MagicMock()

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service.get_supabase', return_value=mock_supabase):
            m = _fresh_import()
            m.reset_profile('user-123')

        mock_supabase.table.return_value.upsert.assert_called_once()
        upsert_data = mock_supabase.table.return_value.upsert.call_args[0][0]
        self.assertEqual(upsert_data['user_id'], 'user-123')
        self.assertEqual(upsert_data['generation_count'], 0)

    def test_save_user_preferences_supabase_disabled_returns_false(self):
        """Supabase 비활성화 시 save_user_preferences는 False 반환"""
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False), \
             patch('services.data.supabase_service.get_supabase', return_value=None):
            m = _fresh_import()
            result = m.save_user_preferences('user-123', {'avoid_keywords': ['혁신적']})

        self.assertFalse(result)

    def test_save_user_preferences_validates_keywords(self):
        """피하고 싶은 표현: 최대 20개, 각 20자 제한"""
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [{'user_id': 'user-123'}]

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service.get_supabase', return_value=mock_supabase):
            m = _fresh_import()
            # 25개 키워드, 각 30자 → 20개 + 각 20자 제한
            long_keywords = [f'keyword_{i}' * 3 for i in range(25)]
            m.save_user_preferences('user-123', {'avoid_keywords': long_keywords})

        mock_supabase.table.return_value.update.assert_called_once()
        updated = mock_supabase.table.return_value.update.call_args[0][0]
        self.assertLessEqual(len(updated['avoid_keywords']), 20)
        for kw in updated['avoid_keywords']:
            self.assertLessEqual(len(kw), 20)


class TestBuildStyleContext(unittest.TestCase):
    """build_style_context 함수 단위 테스트"""

    def setUp(self):
        m = _fresh_import()
        self.build = m.build_style_context

    def test_empty_profile_returns_empty(self):
        """빈 프로필은 빈 문자열 반환"""
        result = self.build({})
        self.assertEqual(result, '')

    def test_disabled_memory_returns_empty(self):
        """style_memory_enabled=False이면 빈 문자열 반환"""
        profile = {
            'style_memory_enabled': False,
            'preferred_styles': [{'style_id': 'blog_seo', 'count': 5}],
            'preferred_length': 'long',
            'preferred_writing_style': 'expert',
            'tone_keywords': [],
            'avoid_keywords': [],
            'custom_instructions': '',
        }
        result = self.build(profile)
        self.assertEqual(result, '')

    def test_context_contains_header(self):
        """컨텍스트에 [사용자 선호 스타일] 헤더 포함"""
        profile = {
            'style_memory_enabled': True,
            'preferred_styles': [{'style_id': 'blog_seo', 'count': 3}],
            'preferred_length': 'medium',
            'preferred_writing_style': 'conversational',
            'tone_keywords': [],
            'avoid_keywords': [],
            'custom_instructions': '',
        }
        result = self.build(profile)
        self.assertIn('[사용자 선호 스타일]', result)

    def test_context_includes_preferred_styles(self):
        """자주 사용 스타일이 컨텍스트에 포함"""
        profile = {
            'style_memory_enabled': True,
            'preferred_styles': [
                {'style_id': 'blog_seo', 'count': 10},
                {'style_id': 'summary', 'count': 5},
            ],
            'preferred_length': 'medium',
            'preferred_writing_style': 'conversational',
            'tone_keywords': [],
            'avoid_keywords': [],
            'custom_instructions': '',
        }
        result = self.build(profile)
        self.assertIn('블로그+SEO', result)
        self.assertIn('요약', result)

    def test_context_includes_avoid_keywords(self):
        """피하고 싶은 표현이 컨텍스트에 포함"""
        profile = {
            'style_memory_enabled': True,
            'preferred_styles': [],
            'preferred_length': 'medium',
            'preferred_writing_style': 'conversational',
            'tone_keywords': [],
            'avoid_keywords': ['혁신적', '획기적'],
            'custom_instructions': '',
        }
        result = self.build(profile)
        self.assertIn('혁신적', result)
        self.assertIn('획기적', result)

    def test_context_includes_custom_instructions(self):
        """커스텀 지시사항이 컨텍스트에 포함"""
        profile = {
            'style_memory_enabled': True,
            'preferred_styles': [],
            'preferred_length': 'short',
            'preferred_writing_style': 'casual',
            'tone_keywords': [],
            'avoid_keywords': [],
            'custom_instructions': '항상 결론 먼저 작성',
        }
        result = self.build(profile)
        self.assertIn('항상 결론 먼저 작성', result)

    def test_top3_styles_only(self):
        """상위 3개 스타일만 표시"""
        profile = {
            'style_memory_enabled': True,
            'preferred_styles': [
                {'style_id': 'blog_seo', 'count': 10},
                {'style_id': 'summary', 'count': 8},
                {'style_id': 'tutorial', 'count': 6},
                {'style_id': 'qna', 'count': 4},
                {'style_id': 'sns_post', 'count': 2},
            ],
            'preferred_length': 'medium',
            'preferred_writing_style': 'conversational',
            'tone_keywords': [],
            'avoid_keywords': [],
            'custom_instructions': '',
        }
        result = self.build(profile)
        # SNS 게시글(하위)은 제외되어야 함
        self.assertNotIn('SNS 게시글', result)
        # 상위 3개는 포함
        self.assertIn('블로그+SEO', result)


class TestIncrementStyleCount(unittest.TestCase):
    """_increment_style_count 내부 헬퍼 테스트"""

    def setUp(self):
        m = _fresh_import()
        self.fn = m._increment_style_count

    def test_empty_list_adds_new(self):
        result = self.fn([], 'blog_seo')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['style_id'], 'blog_seo')
        self.assertEqual(result[0]['count'], 1)

    def test_existing_increments(self):
        existing = [{'style_id': 'blog_seo', 'count': 3}]
        result = self.fn(existing, 'blog_seo')
        self.assertEqual(result[0]['count'], 4)

    def test_new_style_appended(self):
        existing = [{'style_id': 'blog_seo', 'count': 3}]
        result = self.fn(existing, 'summary')
        self.assertEqual(len(result), 2)

    def test_empty_style_id_noop(self):
        existing = [{'style_id': 'blog_seo', 'count': 3}]
        result = self.fn(existing, '')
        self.assertEqual(result, existing)


class TestStyleMemoryApiRoute(unittest.TestCase):
    """스타일 메모리 Flask API 엔드포인트 통합 테스트"""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    def test_get_style_memory_no_auth_returns_401(self):
        """미인증 시 401 반환 (Supabase 활성화 환경)"""
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True):
            res = self.client.get('/api/user/style-memory')
        self.assertEqual(res.status_code, 401)

    def test_get_style_memory_no_supabase_returns_401_or_200(self):
        """Supabase 비활성화 시 401 또는 200"""
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False):
            res = self.client.get('/api/user/style-memory')
        self.assertIn(res.status_code, [200, 401])

    def test_style_memory_routes_registered(self):
        """스타일 메모리 엔드포인트가 앱에 등록되어 있는지 확인"""
        rules = [str(rule) for rule in self.app.url_map.iter_rules()]
        self.assertIn('/api/user/style-memory', rules)
        self.assertIn('/api/user/style-memory/reset', rules)


if __name__ == '__main__':
    unittest.main()
