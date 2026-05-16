"""batch_rewrite_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.content.batch_rewrite_service import (
    batch_rewrite,
    get_available_platforms,
    get_platform_groups,
    _expand_platforms,
    PLATFORM_GROUPS,
    MAX_PLATFORMS,
)


class TestBatchRewrite(unittest.TestCase):

    @patch('services.content.batch_rewrite_service.rewrite_for_platform')
    def test_single_platform(self, mock_rewrite):
        mock_rewrite.return_value = {
            'platform': 'twitter',
            'text': '테스트 트윗',
            'char_count': 7,
            'max_chars': 280,
        }
        result = batch_rewrite('원본 콘텐츠', ['twitter'], 'model')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['success_count'], 1)
        self.assertEqual(result['error_count'], 0)
        self.assertIn('elapsed_ms', result)

    @patch('services.content.batch_rewrite_service.rewrite_for_platform')
    def test_multiple_platforms(self, mock_rewrite):
        def side_effect(content, platform, model):
            return {
                'platform': platform,
                'text': f'{platform} 변환 결과',
                'char_count': 10,
                'max_chars': 280,
            }
        mock_rewrite.side_effect = side_effect
        result = batch_rewrite('원본', ['twitter', 'linkedin'], 'model')
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['success_count'], 2)

    @patch('services.content.batch_rewrite_service.rewrite_for_platform')
    def test_group_expansion(self, mock_rewrite):
        mock_rewrite.return_value = {
            'platform': 'twitter',
            'text': 'ok',
            'char_count': 2,
            'max_chars': 280,
        }
        result = batch_rewrite('원본', ['social'], 'model')
        self.assertEqual(result['total'], len(PLATFORM_GROUPS['social']))

    @patch('services.content.batch_rewrite_service.rewrite_for_platform')
    def test_partial_failure(self, mock_rewrite):
        def side_effect(content, platform, model):
            if platform == 'twitter':
                return {'platform': 'twitter', 'error': '실패'}
            return {'platform': platform, 'text': 'ok', 'char_count': 2, 'max_chars': 3000}
        mock_rewrite.side_effect = side_effect
        result = batch_rewrite('원본', ['twitter', 'linkedin'], 'model')
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['error_count'], 1)
        self.assertEqual(result['success_count'], 1)

    def test_empty_content(self):
        result = batch_rewrite('', ['twitter'], 'model')
        self.assertIn('error', result)

    def test_none_content(self):
        result = batch_rewrite(None, ['twitter'], 'model')
        self.assertIn('error', result)

    def test_empty_platforms(self):
        result = batch_rewrite('콘텐츠', [], 'model')
        self.assertIn('error', result)

    def test_invalid_platforms_only(self):
        result = batch_rewrite('콘텐츠', ['nonexistent'], 'model')
        self.assertIn('error', result)

    @patch('services.content.batch_rewrite_service.rewrite_for_platform')
    def test_max_platform_limit(self, mock_rewrite):
        mock_rewrite.return_value = {
            'platform': 'twitter',
            'text': 'ok',
            'char_count': 2,
            'max_chars': 280,
        }
        many = ['twitter', 'linkedin', 'instagram', 'threads'] * 3
        result = batch_rewrite('원본', many, 'model')
        self.assertLessEqual(result['total'], MAX_PLATFORMS)

    @patch('services.content.batch_rewrite_service.rewrite_for_platform')
    def test_results_ordered(self, mock_rewrite):
        def side_effect(content, platform, model):
            return {'platform': platform, 'text': 'ok', 'char_count': 2, 'max_chars': 280}
        mock_rewrite.side_effect = side_effect
        result = batch_rewrite('원본', ['linkedin', 'twitter'], 'model')
        platforms = [r['platform'] for r in result['results']]
        self.assertEqual(platforms, ['linkedin', 'twitter'])


class TestExpandPlatforms(unittest.TestCase):

    def test_individual_platforms(self):
        self.assertEqual(_expand_platforms(['twitter', 'linkedin']), ['twitter', 'linkedin'])

    def test_group_expansion(self):
        expanded = _expand_platforms(['social'])
        self.assertEqual(expanded, PLATFORM_GROUPS['social'])

    def test_mixed_group_and_individual(self):
        expanded = _expand_platforms(['linkedin', 'social'])
        self.assertIn('linkedin', expanded)
        self.assertIn('twitter', expanded)

    def test_deduplication(self):
        expanded = _expand_platforms(['twitter', 'social'])
        self.assertEqual(expanded.count('twitter'), 1)

    def test_invalid_platform_ignored(self):
        expanded = _expand_platforms(['nonexistent', 'twitter'])
        self.assertEqual(expanded, ['twitter'])

    def test_empty_list(self):
        self.assertEqual(_expand_platforms([]), [])

    def test_case_insensitive(self):
        expanded = _expand_platforms(['Twitter', 'LINKEDIN'])
        self.assertEqual(expanded, ['twitter', 'linkedin'])


class TestGetAvailablePlatforms(unittest.TestCase):

    def test_returns_list(self):
        platforms = get_available_platforms()
        self.assertIsInstance(platforms, list)
        self.assertGreater(len(platforms), 0)

    def test_platform_structure(self):
        platforms = get_available_platforms()
        for p in platforms:
            self.assertIn('id', p)
            self.assertIn('label', p)
            self.assertIn('max_chars', p)
            self.assertIn('tone', p)


class TestGetPlatformGroups(unittest.TestCase):

    def test_returns_dict(self):
        groups = get_platform_groups()
        self.assertIn('social', groups)
        self.assertIn('all', groups)

    def test_group_structure(self):
        groups = get_platform_groups()
        for name, group in groups.items():
            self.assertIn('platforms', group)
            self.assertIn('count', group)
            self.assertEqual(group['count'], len(group['platforms']))


if __name__ == '__main__':
    unittest.main()
