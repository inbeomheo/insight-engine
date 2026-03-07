"""Code Block Quality Checker 서비스 테스트."""
import unittest
from services.code_block_quality_service import check_code_block_quality


class TestCodeBlockQualityChecker(unittest.TestCase):

    def test_empty_content(self):
        result = check_code_block_quality('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_blocks'], 0)

    def test_none_content(self):
        result = check_code_block_quality(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_code_blocks(self):
        content = '코드 블록이 없는 텍스트입니다.'
        result = check_code_block_quality(content)
        self.assertEqual(result['summary']['total_blocks'], 0)

    def test_good_code_block(self):
        content = '설명입니다.\n```python\nprint("hello")\n```\n'
        result = check_code_block_quality(content)
        self.assertEqual(result['summary']['total_blocks'], 1)
        self.assertTrue(result['code_blocks'][0]['has_language_tag'])
        self.assertEqual(result['code_blocks'][0]['language'], 'python')

    def test_missing_language_tag(self):
        content = '설명입니다.\n```\nsome code\n```\n'
        result = check_code_block_quality(content)
        self.assertEqual(result['summary']['missing_language'], 1)
        self.assertFalse(result['code_blocks'][0]['has_language_tag'])

    def test_empty_code_block(self):
        content = '설명입니다.\n```python\n\n```\n'
        result = check_code_block_quality(content)
        self.assertEqual(result['summary']['empty_blocks'], 1)

    def test_long_code_block(self):
        lines = '\n'.join(f'line {i}' for i in range(55))
        content = f'설명입니다.\n```python\n{lines}\n```\n'
        result = check_code_block_quality(content)
        self.assertEqual(result['summary']['long_blocks'], 1)
        self.assertTrue(result['code_blocks'][0]['is_long'])

    def test_multiple_blocks_mixed(self):
        content = """설명입니다.
```python
print("good")
```

```
no language
```

```javascript
console.log("hello")
```
"""
        result = check_code_block_quality(content)
        self.assertEqual(result['summary']['total_blocks'], 3)
        self.assertEqual(result['summary']['missing_language'], 1)

    def test_score_perfect(self):
        content = '```python\nprint("ok")\n```\n'
        result = check_code_block_quality(content)
        self.assertGreaterEqual(result['score'], 80.0)

    def test_score_decreases_with_issues(self):
        content = '```\n\n```\n'
        result = check_code_block_quality(content)
        self.assertLess(result['score'], 100.0)

    def test_suggestions_missing_lang(self):
        content = '```\ncode\n```\n'
        result = check_code_block_quality(content)
        self.assertTrue(any('언어' in s for s in result['suggestions']))

    def test_known_languages(self):
        for lang in ['javascript', 'typescript', 'bash', 'json']:
            content = f'```{lang}\ncode\n```\n'
            result = check_code_block_quality(content)
            self.assertTrue(result['code_blocks'][0]['has_language_tag'])

    def test_return_structure(self):
        content = '```python\ncode\n```\n'
        result = check_code_block_quality(content)
        self.assertIn('code_blocks', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_blocks', result['summary'])
        self.assertIn('missing_language', result['summary'])


if __name__ == '__main__':
    unittest.main()
