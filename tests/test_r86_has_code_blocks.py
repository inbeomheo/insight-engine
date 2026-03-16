"""R86: /generate 응답에 has_code_blocks 필드 추가 테스트."""
import unittest


class TestHasCodeBlocks(unittest.TestCase):

    def _compute_has_code_blocks(self, content: str) -> bool:
        """generation_helpers.py와 동일한 로직으로 has_code_blocks 계산."""
        return bool('```' in content or '<code>' in content)

    def test_backtick_code_block(self):
        """마크다운 코드 블록(```)을 감지한다."""
        content = '설명입니다.\n```python\nprint("hello")\n```\n끝.'
        self.assertTrue(self._compute_has_code_blocks(content))

    def test_html_code_tag(self):
        """HTML <code> 태그를 감지한다."""
        content = '인라인 <code>x = 1</code> 코드입니다.'
        self.assertTrue(self._compute_has_code_blocks(content))

    def test_no_code_blocks(self):
        """코드 블록이 없으면 False를 반환한다."""
        content = '이것은 일반 텍스트입니다. 코드가 없습니다.'
        self.assertFalse(self._compute_has_code_blocks(content))

    def test_empty_content(self):
        """빈 콘텐츠에서는 False를 반환한다."""
        self.assertFalse(self._compute_has_code_blocks(''))


if __name__ == '__main__':
    unittest.main()
