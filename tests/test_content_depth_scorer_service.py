"""Content Depth Scorer 서비스 테스트."""
import unittest
from services.analysis.content_depth_scorer_service import score_content_depth


class TestContentDepthScorer(unittest.TestCase):

    def test_empty_content(self):
        result = score_content_depth('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['depth_level'], 'empty')

    def test_none_content(self):
        result = score_content_depth(None)
        self.assertEqual(result['score'], 0.0)

    def test_surface_content(self):
        content = '간단한 설명입니다. 짧은 텍스트입니다.'
        result = score_content_depth(content)
        self.assertIn(result['summary']['depth_level'], ['surface', 'shallow'])

    def test_content_with_examples(self):
        content = '예를 들어 React는 컴포넌트 기반입니다. 예시로 버튼 컴포넌트가 있습니다.'
        result = score_content_depth(content)
        self.assertGreater(result['depth_indicators']['examples'], 0)

    def test_content_with_evidence(self):
        content = '연구에 따르면 생산성이 30% 향상됩니다. 통계 데이터가 이를 뒷받침합니다.'
        result = score_content_depth(content)
        self.assertGreater(result['depth_indicators']['evidence'], 0)

    def test_content_with_comparisons(self):
        content = 'React vs Vue: 성능 비교 결과입니다. 반면 Angular는 다릅니다.'
        result = score_content_depth(content)
        self.assertGreater(result['depth_indicators']['comparisons'], 0)

    def test_content_with_causal(self):
        content = '성능이 저하되는 이유는 메모리 부족 때문에 발생합니다. 따라서 최적화가 필요합니다.'
        result = score_content_depth(content)
        self.assertGreater(result['depth_indicators']['causal_reasoning'], 0)

    def test_content_with_definitions(self):
        content = 'API의 정의는 프로그래밍 인터페이스를 의미합니다.'
        result = score_content_depth(content)
        self.assertGreater(result['depth_indicators']['definitions'], 0)

    def test_content_with_code(self):
        content = '코드 예시입니다.\n```python\nprint("hello")\n```\n인라인 `code`도 있습니다.'
        result = score_content_depth(content)
        self.assertGreater(result['depth_indicators']['code_blocks'], 0)

    def test_deep_content(self):
        content = """
예를 들어 React 컴포넌트가 있습니다.
연구에 따르면 성능이 50% 향상됩니다.
반면 Vue는 다른 접근법을 사용합니다.
이것은 때문에 메모리 관리가 중요합니다.
API의 정의는 인터페이스입니다.
```python
print("example")
```
인라인 `code`도 포함합니다.
"""
        result = score_content_depth(content)
        self.assertGreaterEqual(result['score'], 50.0)

    def test_english_evidence(self):
        content = 'Research shows that the data supports this claim. The study found significant results.'
        result = score_content_depth(content)
        self.assertGreater(result['depth_indicators']['evidence'], 0)

    def test_english_examples(self):
        content = 'For example, React uses virtual DOM. For instance, it improves performance.'
        result = score_content_depth(content)
        self.assertGreater(result['depth_indicators']['examples'], 0)

    def test_suggestions_shallow(self):
        content = '간단한 설명입니다. 추가 내용 없이 짧습니다.'
        result = score_content_depth(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '테스트 콘텐츠입니다.'
        result = score_content_depth(content)
        self.assertIn('depth_indicators', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_indicators', result['summary'])
        self.assertIn('depth_level', result['summary'])
        self.assertIn('word_count', result['summary'])


if __name__ == '__main__':
    unittest.main()
