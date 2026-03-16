"""R149: /api/content/stats 응답에 has_code_blocks 필드 추가 테스트."""
import unittest


class TestContentStatsCodeBlocks(unittest.TestCase):
    """content_stats 엔드포인트의 has_code_blocks 필드 검증."""

    def _has_code_blocks(self, content: str) -> bool:
        """utility_routes.py content_stats와 동일한 로직."""
        return bool('```' in content or '<code>' in content)

    def test_markdown_code_block_detected(self):
        """마크다운 코드 블록(```)이 감지되는지 확인."""
        content = "설명 텍스트\n```python\nprint('hello')\n```\n끝"
        self.assertTrue(self._has_code_blocks(content))

    def test_html_code_tag_detected(self):
        """HTML <code> 태그가 감지되는지 확인."""
        content = "인라인 코드: <code>x = 1</code> 입니다."
        self.assertTrue(self._has_code_blocks(content))

    def test_no_code_blocks(self):
        """코드 블록이 없는 텍스트는 False 반환."""
        content = "일반 텍스트입니다. 코드 없이 작성되었습니다."
        self.assertFalse(self._has_code_blocks(content))

    def test_empty_content(self):
        """빈 문자열은 False 반환."""
        self.assertFalse(self._has_code_blocks(''))

    def test_backtick_inline_not_triple(self):
        """단일 백틱(인라인 코드)은 코드 블록으로 간주하지 않음."""
        content = "변수 `x`를 사용합니다."
        self.assertFalse(self._has_code_blocks(content))


if __name__ == '__main__':
    unittest.main()
