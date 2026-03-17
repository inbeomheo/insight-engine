"""Table of Contents Generator 서비스 테스트."""
import unittest
from services.content.toc_generator_service import generate_toc, _slugify


class TestTocGenerator(unittest.TestCase):

    def test_empty_content(self):
        result = generate_toc('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['total_headings'], 0)

    def test_none_content(self):
        result = generate_toc(None)
        self.assertEqual(result['score'], 0.0)

    def test_no_headings(self):
        content = '헤딩이 없는 평문입니다. 구조가 없습니다.'
        result = generate_toc(content)
        self.assertEqual(len(result['toc']), 0)
        self.assertEqual(result['score'], 30.0)

    def test_basic_headings(self):
        content = """# 제목
본문입니다.

## 섹션 1
내용 1.

## 섹션 2
내용 2.

### 하위 섹션
하위 내용."""
        result = generate_toc(content)
        self.assertEqual(result['summary']['total_headings'], 4)
        self.assertEqual(len(result['toc']), 4)

    def test_max_depth_filter(self):
        content = """# H1
## H2
### H3
#### H4"""
        result = generate_toc(content, max_depth=2)
        self.assertEqual(result['summary']['total_headings'], 2)

    def test_anchor_generation(self):
        content = '## 테스트 헤딩입니다'
        result = generate_toc(content)
        if result['toc']:
            self.assertIn('anchor', result['toc'][0])
            self.assertNotEqual(result['toc'][0]['anchor'], '')

    def test_markdown_toc_format(self):
        content = """# 제목
## 섹션 A
## 섹션 B"""
        result = generate_toc(content)
        self.assertIn('markdown_toc', result)
        self.assertIn('섹션 A', result['markdown_toc'])
        self.assertIn('섹션 B', result['markdown_toc'])

    def test_multiple_h1_warning(self):
        content = """# 제목 1
# 제목 2
## 섹션"""
        result = generate_toc(content)
        # H1이 2개면 구조 이슈
        self.assertFalse(result['summary']['structure_valid'])

    def test_level_skip_detection(self):
        content = """# 제목
### 건너뛴 헤딩"""
        result = generate_toc(content)
        self.assertFalse(result['summary']['structure_valid'])

    def test_depth_distribution(self):
        content = """# 제목
## 섹션 1
## 섹션 2
### 하위 1"""
        result = generate_toc(content)
        dist = result['summary']['depth_distribution']
        self.assertEqual(dist.get('h1', 0), 1)
        self.assertEqual(dist.get('h2', 0), 2)
        self.assertEqual(dist.get('h3', 0), 1)

    def test_score_good_structure(self):
        content = """# 제목
## 소개
## 본론
### 세부 1
### 세부 2
## 결론"""
        result = generate_toc(content)
        self.assertGreaterEqual(result['score'], 70.0)

    def test_suggestions_exist(self):
        content = '## 단일 헤딩'
        result = generate_toc(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '## 테스트'
        result = generate_toc(content)
        self.assertIn('toc', result)
        self.assertIn('markdown_toc', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_headings', result['summary'])
        self.assertIn('structure_valid', result['summary'])
        self.assertIn('depth_distribution', result['summary'])


class TestDuplicateAnchor(unittest.TestCase):
    """동일 텍스트 헤딩의 앵커 ID 중복 방지 테스트"""

    def test_duplicate_headings_get_unique_anchors(self):
        """동일 텍스트 헤딩이 여러 개면 앵커에 번호 접미사 추가"""
        content = """# 제목
## 결론
## 중간
## 결론"""
        result = generate_toc(content)
        anchors = [h['anchor'] for h in result['toc']]
        # 모든 앵커가 고유해야 함
        self.assertEqual(len(anchors), len(set(anchors)))
        # 첫 '결론'은 접미사 없음, 두 번째는 -1 접미사
        conclusion_anchors = [h['anchor'] for h in result['toc'] if h['text'] == '결론']
        self.assertEqual(len(conclusion_anchors), 2)
        self.assertNotEqual(conclusion_anchors[0], conclusion_anchors[1])

    def test_single_heading_no_suffix(self):
        """단일 헤딩은 접미사 없음"""
        content = '## 유일한 헤딩'
        result = generate_toc(content)
        self.assertNotIn('-', result['toc'][0]['anchor'].split('유일한-헤딩')[-1])


class TestSlugifyEdgeCases(unittest.TestCase):
    """_slugify 엣지 케이스 테스트"""

    def test_special_chars_only_returns_fallback(self):
        """특수문자만 있으면 'heading' 폴백 반환"""
        self.assertEqual(_slugify('!@#$%^&*()'), 'heading')

    def test_empty_string_returns_fallback(self):
        """빈 문자열은 'heading' 폴백 반환"""
        self.assertEqual(_slugify(''), 'heading')

    def test_spaces_only_returns_fallback(self):
        """공백만 있으면 'heading' 폴백 반환"""
        self.assertEqual(_slugify('   '), 'heading')

    def test_korean_text(self):
        """한글 텍스트는 정상 처리"""
        self.assertEqual(_slugify('한글 제목'), '한글-제목')

    def test_mixed_text(self):
        """영문+숫자+특수문자 혼합"""
        result = _slugify('Hello World 123!')
        self.assertEqual(result, 'hello-world-123')


class TestGenerateTocEdgeCases(unittest.TestCase):
    """generate_toc 엣지 케이스 테스트"""

    def test_max_depth_limits_headings(self):
        """max_depth보다 깊은 헤딩은 제외"""
        content = '# H1\n## H2\n### H3\n#### H4'
        result = generate_toc(content, max_depth=2)
        levels = [h['level'] for h in result['toc']]
        self.assertNotIn(3, levels)
        self.assertNotIn(4, levels)

    def test_max_depth_1(self):
        """max_depth=1이면 H1만 추출"""
        content = '# 제목\n## 소제목\n### 하위'
        result = generate_toc(content, max_depth=1)
        self.assertEqual(len(result['toc']), 1)
        self.assertEqual(result['toc'][0]['level'], 1)

    def test_structure_validation_skip_levels(self):
        """레벨 건너뛰기 감지 (H1→H3)"""
        content = '# 제목\n### 하위 (H2 건너뜀)'
        result = generate_toc(content)
        self.assertFalse(result['summary']['structure_valid'])

    def test_multiple_h1_detected(self):
        """H1 여러 개 감지"""
        content = '# 제목1\n## 내용\n# 제목2'
        result = generate_toc(content)
        self.assertFalse(result['summary']['structure_valid'])


if __name__ == '__main__':
    unittest.main()
