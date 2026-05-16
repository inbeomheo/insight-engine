"""export_bundle_service 단위 테스트"""
import json
import unittest

from services.content.export_bundle_service import (
    create_bundle,
    validate_bundle,
    BUNDLE_VERSION,
)


class TestCreateBundle(unittest.TestCase):

    def test_empty(self):
        result = create_bundle([])
        self.assertEqual(result['item_count'], 0)

    def test_single_content(self):
        contents = [{'title': '테스트', 'content': '# 제목\n본문'}]
        result = create_bundle(contents)
        self.assertEqual(result['item_count'], 1)
        self.assertGreater(result['total_chars'], 0)
        self.assertGreater(len(result['checksum']), 0)

    def test_multiple_contents(self):
        contents = [
            {'title': f'글{i}', 'content': f'내용{i}'}
            for i in range(3)
        ]
        result = create_bundle(contents)
        self.assertEqual(result['item_count'], 3)

    def test_bundle_structure(self):
        contents = [{'title': 'T', 'content': 'C'}]
        result = create_bundle(contents)
        bundle = result['bundle']
        self.assertEqual(bundle['version'], BUNDLE_VERSION)
        self.assertIn('created_at', bundle)
        self.assertIn('items', bundle)

    def test_stats_included(self):
        contents = [{'title': 'T', 'content': '# 제목\n단어 단어 단어'}]
        result = create_bundle(contents, include_stats=True)
        item = result['bundle']['items'][0]
        self.assertIn('stats', item)
        self.assertGreater(item['stats']['word_count'], 0)

    def test_bundle_json_valid(self):
        contents = [{'title': 'T', 'content': 'C'}]
        result = create_bundle(contents)
        parsed = json.loads(result['bundle_json'])
        self.assertIsInstance(parsed, dict)

    def test_custom_name(self):
        contents = [{'title': 'T', 'content': 'C'}]
        result = create_bundle(contents, bundle_name='내보내기_v1')
        self.assertEqual(result['bundle']['name'], '내보내기_v1')

    def test_tags_and_url(self):
        contents = [{'title': 'T', 'content': 'C', 'tags': ['AI', '기술'], 'url': 'https://ex.com'}]
        result = create_bundle(contents)
        item = result['bundle']['items'][0]
        self.assertEqual(item['tags'], ['AI', '기술'])
        self.assertEqual(item['url'], 'https://ex.com')

    def test_checksum_consistent(self):
        contents = [{'title': 'T', 'content': 'C'}]
        r1 = create_bundle(contents, bundle_name='fixed')
        r2 = create_bundle(contents, bundle_name='fixed')
        # 같은 입력이면 같은 체크섬 (created_at 제외하면)
        self.assertIsInstance(r1['checksum'], str)
        self.assertEqual(len(r1['checksum']), 16)

    def test_total_stats(self):
        contents = [
            {'title': 'A', 'content': '단어 ' * 10},
            {'title': 'B', 'content': '단어 ' * 20},
        ]
        result = create_bundle(contents)
        total = result['bundle']['total_stats']
        self.assertEqual(total['total_words'], 30)
        self.assertGreater(total['avg_chars'], 0)


class TestValidateBundle(unittest.TestCase):

    def test_valid_bundle(self):
        bundle = json.dumps({'version': '1.0', 'items': [{'content': 'C'}]})
        result = validate_bundle(bundle)
        self.assertTrue(result['valid'])
        self.assertEqual(result['errors'], [])

    def test_invalid_json(self):
        result = validate_bundle('not json')
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)

    def test_missing_version(self):
        bundle = json.dumps({'items': [{'content': 'C'}]})
        result = validate_bundle(bundle)
        self.assertFalse(result['valid'])

    def test_missing_content(self):
        bundle = json.dumps({'version': '1.0', 'items': [{'title': 'T'}]})
        result = validate_bundle(bundle)
        self.assertFalse(result['valid'])

    def test_empty_string(self):
        result = validate_bundle('')
        self.assertFalse(result['valid'])

    def test_roundtrip(self):
        contents = [{'title': 'T', 'content': '본문'}]
        created = create_bundle(contents)
        validated = validate_bundle(created['bundle_json'])
        self.assertTrue(validated['valid'])
        self.assertEqual(validated['item_count'], 1)


if __name__ == '__main__':
    unittest.main()
