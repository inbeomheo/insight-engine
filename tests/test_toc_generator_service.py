"""Table of Contents Generator 서비스 테스트."""
import unittest
from services.content.toc_generator_service import generate_toc, generate_numbered_toc


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


class TestNumberedToc(unittest.TestCase):
    """generate_numbered_toc 테스트"""

    def test_empty_content(self):
        result = generate_numbered_toc('')
        self.assertEqual(result['numbered_toc'], [])
        self.assertEqual(result['markdown'], '')

    def test_h2_numbering(self):
        """H2 기본 번호 매기기"""
        content = """# 제목
## 소개
## 본론
## 결론"""
        result = generate_numbered_toc(content)
        numbers = [item['number'] for item in result['numbered_toc'] if item['level'] == 2]
        self.assertEqual(numbers, ['1.', '2.', '3.'])

    def test_h3_nested_numbering(self):
        """H3 계층적 번호 매기기"""
        content = """# 제목
## 섹션 1
### 항목 A
### 항목 B
## 섹션 2
### 항목 C"""
        result = generate_numbered_toc(content)
        numbers = [item['number'] for item in result['numbered_toc'] if item['number']]
        self.assertEqual(numbers, ['1.', '1.1.', '1.2.', '2.', '2.1.'])

    def test_h1_no_number(self):
        """H1은 번호 없음"""
        content = '# 제목\n## 섹션'
        result = generate_numbered_toc(content)
        h1 = [item for item in result['numbered_toc'] if item['level'] == 1]
        self.assertEqual(h1[0]['number'], '')

    def test_markdown_output(self):
        """마크다운 형식 출력"""
        content = '## 섹션 1\n## 섹션 2'
        result = generate_numbered_toc(content)
        self.assertIn('1.', result['markdown'])
        self.assertIn('2.', result['markdown'])

    def test_no_headings(self):
        result = generate_numbered_toc('본문만 있는 텍스트')
        self.assertEqual(result['numbered_toc'], [])


if __name__ == '__main__':
    unittest.main()
