"""quality_service.calculate_comprehensive_score 단위 테스트"""
import unittest

from services.quality.quality_service import calculate_comprehensive_score


class TestComprehensiveScore(unittest.TestCase):

    def test_empty_content(self):
        result = calculate_comprehensive_score("")
        self.assertEqual(result["total_score"], 0)
        self.assertEqual(result["seo"], 0)

    def test_basic_content(self):
        content = "간단한 테스트 콘텐츠입니다."
        result = calculate_comprehensive_score(content)
        self.assertIn("total_score", result)
        self.assertIn("seo", result)
        self.assertIn("readability", result)
        self.assertIn("originality", result)
        self.assertIn("structure", result)
        self.assertGreater(result["total_score"], 0)

    def test_well_structured_content(self):
        content = """# 제목

## 소제목 1

첫 번째 문단입니다. 내용을 설명합니다.

- 항목 1
- 항목 2
- 항목 3

## 소제목 2

두 번째 문단입니다. [링크](https://example.com) 포함.

## 소제목 3

세 번째 문단입니다.

- 항목 A
- 항목 B
"""
        result = calculate_comprehensive_score(content)
        # 구조가 잘 갖춰진 콘텐츠는 높은 점수
        self.assertGreater(result["structure"], 60)
        self.assertGreater(result["seo"], 60)

    def test_cliche_penalty(self):
        content = "놀라운 혁신적 획기적 기술입니다. 최고의 게임체인저입니다. 압도적 경이로운 성능."
        result = calculate_comprehensive_score(content)
        no_cliche = calculate_comprehensive_score("일반적인 기술에 대한 설명입니다. 다양한 방법으로 접근합니다.")
        # 금지 표현이 많으면 독창성 점수 감소
        self.assertLess(result["originality"], no_cliche["originality"])

    def test_score_range(self):
        content = "테스트 " * 100
        result = calculate_comprehensive_score(content)
        for key in ["total_score", "seo", "readability", "originality", "structure"]:
            self.assertGreaterEqual(result[key], 0)
            self.assertLessEqual(result[key], 100)

    def test_details_included(self):
        result = calculate_comprehensive_score("테스트 콘텐츠 입니다")
        self.assertIn("details", result)
        self.assertIn("char_count", result["details"])
        self.assertIn("word_count", result["details"])


if __name__ == '__main__':
    unittest.main()
