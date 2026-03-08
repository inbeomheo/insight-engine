"""style_memory_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.style_memory_service import (
    STYLE_LABELS,
    WRITING_STYLE_LABELS,
    LENGTH_LABELS,
    DEFAULT_PROFILE,
    _increment_style_count,
    _get_dominant_value,
    build_style_context,
    get_profile,
    update_profile,
    save_user_preferences,
    reset_profile,
    _db_op,
)


class TestConstants(unittest.TestCase):

    def test_style_labels(self):
        """스타일 레이블 매핑"""
        self.assertIn('blog_seo', STYLE_LABELS)
        self.assertEqual(STYLE_LABELS['blog_seo'], '블로그+SEO')

    def test_writing_style_labels(self):
        """문체 레이블 매핑"""
        self.assertIn('conversational', WRITING_STYLE_LABELS)

    def test_length_labels(self):
        """길이 레이블 매핑"""
        self.assertIn('medium', LENGTH_LABELS)
        self.assertEqual(LENGTH_LABELS['medium'], '보통')

    def test_default_profile(self):
        """기본 프로필 구조"""
        self.assertEqual(DEFAULT_PROFILE['preferred_length'], 'medium')
        self.assertEqual(DEFAULT_PROFILE['preferred_writing_style'], 'conversational')
        self.assertTrue(DEFAULT_PROFILE['style_memory_enabled'])
        self.assertEqual(DEFAULT_PROFILE['generation_count'], 0)


class TestIncrementStyleCount(unittest.TestCase):

    def test_new_style(self):
        """새 스타일 추가"""
        result = _increment_style_count([], 'blog_seo')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['style_id'], 'blog_seo')
        self.assertEqual(result[0]['count'], 1)

    def test_existing_style(self):
        """기존 스타일 카운트 증가"""
        styles = [{'style_id': 'blog_seo', 'count': 3}]
        result = _increment_style_count(styles, 'blog_seo')
        self.assertEqual(result[0]['count'], 4)

    def test_empty_style_id(self):
        """빈 스타일 ID → 변경 없음"""
        styles = [{'style_id': 'summary', 'count': 1}]
        result = _increment_style_count(styles, '')
        self.assertEqual(result, styles)

    def test_multiple_styles(self):
        """여러 스타일 중 하나만 증가"""
        styles = [
            {'style_id': 'blog_seo', 'count': 5},
            {'style_id': 'summary', 'count': 2},
        ]
        result = _increment_style_count(styles, 'summary')
        self.assertEqual(result[0]['count'], 5)
        self.assertEqual(result[1]['count'], 3)


class TestGetDominantValue(unittest.TestCase):

    def test_returns_fallback(self):
        """현재 구현은 fallback 반환"""
        result = _get_dominant_value([], 'length', 'medium')
        self.assertEqual(result, 'medium')


class TestBuildStyleContext(unittest.TestCase):

    def test_empty_profile(self):
        """빈 프로필 → 빈 문자열"""
        self.assertEqual(build_style_context({}), '')

    def test_none_profile(self):
        """None → 빈 문자열"""
        self.assertEqual(build_style_context(None), '')

    def test_disabled(self):
        """비활성화 → 빈 문자열"""
        profile = dict(DEFAULT_PROFILE)
        profile['style_memory_enabled'] = False
        self.assertEqual(build_style_context(profile), '')

    def test_basic_context(self):
        """기본 컨텍스트 생성"""
        profile = dict(DEFAULT_PROFILE)
        profile['style_memory_enabled'] = True
        result = build_style_context(profile)
        self.assertIn('[사용자 선호 스타일]', result)
        self.assertIn('선호 글 길이: 보통', result)
        self.assertIn('선호 문체: 대화체', result)

    def test_with_preferred_styles(self):
        """선호 스타일 포함"""
        profile = dict(DEFAULT_PROFILE)
        profile['preferred_styles'] = [
            {'style_id': 'blog_seo', 'count': 10},
            {'style_id': 'summary', 'count': 5},
        ]
        result = build_style_context(profile)
        self.assertIn('블로그+SEO', result)

    def test_with_avoid_keywords(self):
        """피하는 표현 포함"""
        profile = dict(DEFAULT_PROFILE)
        profile['avoid_keywords'] = ['놀라운', '혁신적']
        result = build_style_context(profile)
        self.assertIn('피하는 표현', result)
        self.assertIn('놀라운', result)

    def test_with_custom_instructions(self):
        """커스텀 지시사항 포함"""
        profile = dict(DEFAULT_PROFILE)
        profile['custom_instructions'] = '항상 예시를 포함해주세요'
        result = build_style_context(profile)
        self.assertIn('추가 지시', result)
        self.assertIn('예시를 포함', result)

    def test_with_tone_keywords(self):
        """톤 키워드 포함"""
        profile = dict(DEFAULT_PROFILE)
        profile['tone_keywords'] = ['친근한', '전문적']
        result = build_style_context(profile)
        self.assertIn('선호 톤', result)


class TestDbOp(unittest.TestCase):

    def test_success(self):
        """정상 실행"""
        self.assertEqual(_db_op('test', 'default', lambda: 42), 42)

    def test_error(self):
        """예외 → 기본값"""
        self.assertEqual(_db_op('test', 'fallback', lambda: 1/0), 'fallback')


class TestSupabaseDisabled(unittest.TestCase):

    @patch('services.style_memory_service.is_supabase_enabled', return_value=False)
    def test_get_profile(self, mock_sb):
        """Supabase 비활성 → 기본 프로필"""
        result = get_profile('user1')
        self.assertEqual(result['preferred_length'], 'medium')

    @patch('services.style_memory_service.is_supabase_enabled', return_value=False)
    def test_update_profile(self, mock_sb):
        """Supabase 비활성 → None (무시)"""
        result = update_profile('user1', {'style': 'blog_seo'})
        self.assertIsNone(result)

    @patch('services.style_memory_service.is_supabase_enabled', return_value=False)
    def test_save_preferences(self, mock_sb):
        """Supabase 비활성 → False"""
        self.assertFalse(save_user_preferences('user1', {'avoid_keywords': ['test']}))

    @patch('services.style_memory_service.is_supabase_enabled', return_value=False)
    def test_reset_profile(self, mock_sb):
        """Supabase 비활성 → False"""
        self.assertFalse(reset_profile('user1'))


if __name__ == '__main__':
    unittest.main()
