"""infographic_service 단위 테스트"""
import unittest

from services.media.infographic_service import (
    generate_infographic, _extract_key_points, _extract_stats
)


class TestExtractKeyPoints(unittest.TestCase):
    """_extract_key_points 테스트"""

    def test_heading_extraction(self):
        """마크다운 헤딩 추출"""
        md = '# 메인 제목\n## 부제목 영역\n### 소제목 영역'
        points = _extract_key_points(md)
        self.assertIn('메인 제목', points)
        self.assertIn('부제목 영역', points)

    def test_list_item_extraction(self):
        """리스트 아이템 추출"""
        md = '- 첫 번째 항목입니다\n- 두 번째 항목입니다\n- 세 번째 항목입니다\n- 네 번째 항목입니다'
        points = _extract_key_points(md)
        self.assertGreaterEqual(len(points), 4)

    def test_numbered_list_extraction(self):
        """번호 리스트 추출"""
        md = '1. 첫 번째 단계입니다\n2. 두 번째 단계입니다\n3. 세 번째 단계입니다\n4. 네 번째 단계입니다'
        points = _extract_key_points(md)
        self.assertGreaterEqual(len(points), 4)

    def test_max_8_points(self):
        """최대 8개 포인트"""
        md = '\n'.join(f'## 포인트 번호 {i}' for i in range(15))
        points = _extract_key_points(md)
        self.assertLessEqual(len(points), 8)

    def test_strips_markdown_formatting(self):
        """마크다운 서식 제거"""
        md = '## **볼드 제목** _이탤릭_'
        points = _extract_key_points(md)
        self.assertTrue(any('볼드 제목' in p for p in points))

    def test_empty_content(self):
        """빈 콘텐츠"""
        self.assertEqual(_extract_key_points(''), [])


class TestExtractStats(unittest.TestCase):
    """_extract_stats 테스트"""

    def test_percentage(self):
        """퍼센트 추출"""
        result = _extract_stats('성공률 95%')
        self.assertTrue(any(s['value'] == '95' for s in result))

    def test_max_4_stats(self):
        """최대 4개 통계"""
        text = ' '.join(f'{i*100}명' for i in range(10, 20))
        result = _extract_stats(text)
        self.assertLessEqual(len(result), 4)

    def test_short_numbers_excluded(self):
        """1자리 숫자 제외"""
        result = _extract_stats('1개 2건')
        self.assertEqual(result, [])


class TestGenerateInfographic(unittest.TestCase):
    """generate_infographic 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠 시 안내 메시지"""
        result = generate_infographic('', '제목')
        self.assertIn('콘텐츠가 없습니다', result)

    def test_returns_html(self):
        """HTML 반환"""
        md = '## 핵심 포인트\n- 중요한 내용입니다\n- 또 다른 포인트입니다'
        result = generate_infographic(md, '테스트 인포그래픽')
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('테스트 인포그래픽', result)

    def test_xss_escaped(self):
        """XSS 이스케이프"""
        result = generate_infographic('내용', '<script>alert(1)</script>')
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)

    def test_none_title_fallback(self):
        """None 제목 시 기본값"""
        result = generate_infographic('## 포인트', None)
        self.assertIn('인포그래픽', result)

    def test_key_points_in_output(self):
        """핵심 포인트가 출력에 포함"""
        md = '## 파이썬 프로그래밍\n## 자바스크립트 개발'
        result = generate_infographic(md, '제목')
        self.assertIn('파이썬 프로그래밍', result)


if __name__ == '__main__':
    unittest.main()
