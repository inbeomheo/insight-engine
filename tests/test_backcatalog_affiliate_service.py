"""
백카탈로그 제휴 매칭 서비스 단위 테스트
"""
import unittest

from services.backcatalog_affiliate_service import (
    AffiliateMatch,
    scan_affiliate_opportunities,
    rank_opportunities,
    CATEGORY_KEYWORDS,
    VALID_PLACEMENTS,
    _normalize_text,
    _find_matching_keywords,
    _calculate_relevance,
)


class TestScanAffiliateOpportunities(unittest.TestCase):
    """scan_affiliate_opportunities 함수 테스트"""

    def test_빈_아카이브_빈_리스트(self):
        """빈 아카이브 → 빈 리스트"""
        result = scan_affiliate_opportunities([])
        self.assertEqual(result, [])

    def test_기술_키워드_매칭(self):
        """기술 관련 키워드가 포함된 콘텐츠 매칭"""
        archive = [
            {"id": "1", "title": "AI 프로그래밍 입문", "content": "인공지능과 머신러닝 기초"}
        ]
        matches = scan_affiliate_opportunities(archive)
        tech_matches = [m for m in matches if m.affiliate_category == "tech"]
        self.assertGreater(len(tech_matches), 0)
        self.assertIsInstance(tech_matches[0], AffiliateMatch)

    def test_교육_키워드_매칭(self):
        """교육 관련 키워드 매칭"""
        archive = [
            {"id": "2", "title": "온라인 강의 추천", "content": "학습에 도움되는 교육 플랫폼"}
        ]
        matches = scan_affiliate_opportunities(archive)
        edu_matches = [m for m in matches if m.affiliate_category == "education"]
        self.assertGreater(len(edu_matches), 0)

    def test_라이프스타일_키워드_매칭(self):
        """라이프스타일 관련 키워드 매칭"""
        archive = [
            {"id": "3", "title": "건강한 다이어트", "content": "운동과 요가로 건강한 생활"}
        ]
        matches = scan_affiliate_opportunities(archive)
        life_matches = [m for m in matches if m.affiliate_category == "lifestyle"]
        self.assertGreater(len(life_matches), 0)

    def test_금융_키워드_매칭(self):
        """금융 관련 키워드 매칭"""
        archive = [
            {"id": "4", "title": "주식 투자 가이드", "content": "ETF와 펀드로 안전한 재테크"}
        ]
        matches = scan_affiliate_opportunities(archive)
        fin_matches = [m for m in matches if m.affiliate_category == "finance"]
        self.assertGreater(len(fin_matches), 0)

    def test_매칭_없는_콘텐츠_제외(self):
        """키워드 매칭이 없는 콘텐츠는 결과에서 제외"""
        archive = [
            {"id": "5", "title": "xyzabc", "content": "무의미한 텍스트 123456"}
        ]
        matches = scan_affiliate_opportunities(archive)
        self.assertEqual(len(matches), 0)

    def test_다중_카테고리_매칭(self):
        """하나의 콘텐츠가 여러 카테고리에 매칭 가능"""
        archive = [
            {
                "id": "6",
                "title": "AI 투자 강의",
                "content": "인공지능 기술로 주식 투자를 학습하는 교육 프로그램",
            }
        ]
        matches = scan_affiliate_opportunities(archive)
        categories = {m.affiliate_category for m in matches}
        # tech + education + finance 최소 2개 이상
        self.assertGreaterEqual(len(categories), 2)

    def test_결과_필드_구조(self):
        """AffiliateMatch 필드가 올바르게 채워지는지 확인"""
        archive = [
            {"id": "7", "title": "프로그래밍 기초", "content": "코딩 입문"}
        ]
        matches = scan_affiliate_opportunities(archive)
        self.assertGreater(len(matches), 0)
        match = matches[0]
        self.assertEqual(match.content_id, "7")
        self.assertEqual(match.content_title, "프로그래밍 기초")
        self.assertIsInstance(match.matched_keywords, list)
        self.assertIn(match.affiliate_category, CATEGORY_KEYWORDS.keys())
        self.assertGreater(match.estimated_relevance, 0.0)
        self.assertIn(match.suggested_placement, VALID_PLACEMENTS)

    def test_빈_콘텐츠_항목_스킵(self):
        """제목/본문이 모두 비어있는 항목은 스킵"""
        archive = [
            {"id": "8", "title": "", "content": ""}
        ]
        matches = scan_affiliate_opportunities(archive)
        self.assertEqual(len(matches), 0)

    def test_content_필드_없는_경우(self):
        """content 필드가 없어도 title만으로 매칭"""
        archive = [
            {"id": "9", "title": "AI 프로그래밍 기술 앱 개발"}
        ]
        matches = scan_affiliate_opportunities(archive)
        self.assertGreater(len(matches), 0)

    def test_suggested_placement_카테고리별(self):
        """카테고리별 올바른 배치 제안"""
        archive = [
            {"id": "t1", "title": "기술 앱 소프트웨어", "content": ""},
            {"id": "t2", "title": "강의 학습 교육", "content": ""},
            {"id": "t3", "title": "건강 운동 다이어트", "content": ""},
            {"id": "t4", "title": "투자 저축 주식", "content": ""},
        ]
        matches = scan_affiliate_opportunities(archive)
        placement_map = {m.content_id: m.suggested_placement for m in matches}
        # 각 카테고리의 기본 배치 확인
        if "t1" in placement_map:
            self.assertEqual(placement_map["t1"], "inline_link")
        if "t2" in placement_map:
            self.assertEqual(placement_map["t2"], "end_of_article")
        if "t3" in placement_map:
            self.assertEqual(placement_map["t3"], "sidebar")
        if "t4" in placement_map:
            self.assertEqual(placement_map["t4"], "comparison_table")

    def test_대량_아카이브_처리(self):
        """100개 항목 아카이브 정상 처리"""
        archive = [
            {"id": str(i), "title": f"AI 기술 기사 {i}", "content": "인공지능 개발"}
            for i in range(100)
        ]
        matches = scan_affiliate_opportunities(archive)
        self.assertGreater(len(matches), 0)


class TestRankOpportunities(unittest.TestCase):
    """rank_opportunities 함수 테스트"""

    def test_빈_리스트(self):
        """빈 리스트 → 빈 리스트"""
        result = rank_opportunities([])
        self.assertEqual(result, [])

    def test_relevance_내림차순_정렬(self):
        """estimated_relevance 기준 내림차순"""
        matches = [
            AffiliateMatch("1", "저", ["a"], "tech", 0.3, "inline_link"),
            AffiliateMatch("2", "고", ["a", "b", "c"], "tech", 0.9, "inline_link"),
            AffiliateMatch("3", "중", ["a", "b"], "tech", 0.6, "inline_link"),
        ]
        ranked = rank_opportunities(matches)
        self.assertEqual(ranked[0].content_id, "2")
        self.assertEqual(ranked[1].content_id, "3")
        self.assertEqual(ranked[2].content_id, "1")

    def test_동일_relevance_키워드수_정렬(self):
        """relevance 동일 시 키워드 수가 많은 순"""
        matches = [
            AffiliateMatch("1", "A", ["x"], "tech", 0.5, "inline_link"),
            AffiliateMatch("2", "B", ["x", "y", "z"], "tech", 0.5, "inline_link"),
        ]
        ranked = rank_opportunities(matches)
        self.assertEqual(ranked[0].content_id, "2")

    def test_원본_리스트_미변경(self):
        """정렬 시 원본 리스트는 변경되지 않음"""
        matches = [
            AffiliateMatch("1", "A", ["a"], "tech", 0.3, "inline_link"),
            AffiliateMatch("2", "B", ["b"], "tech", 0.9, "inline_link"),
        ]
        original_first_id = matches[0].content_id
        rank_opportunities(matches)
        self.assertEqual(matches[0].content_id, original_first_id)


class TestHelperFunctions(unittest.TestCase):
    """내부 헬퍼 함수 테스트"""

    def test_normalize_text_소문자_변환(self):
        self.assertEqual(_normalize_text("Hello World"), "hello world")

    def test_normalize_text_공백_정리(self):
        self.assertEqual(_normalize_text("  다중   공백  "), "다중 공백")

    def test_find_matching_keywords_매칭(self):
        matched = _find_matching_keywords("AI 기술과 프로그래밍", "tech")
        self.assertIn("기술", matched)
        self.assertIn("프로그래밍", matched)

    def test_find_matching_keywords_매칭_없음(self):
        matched = _find_matching_keywords("무관한 내용", "tech")
        self.assertEqual(matched, [])

    def test_calculate_relevance_정상(self):
        rel = _calculate_relevance(5, 100)
        self.assertGreater(rel, 0.0)
        self.assertLessEqual(rel, 1.0)

    def test_calculate_relevance_제로_매칭(self):
        self.assertEqual(_calculate_relevance(0, 100), 0.0)

    def test_calculate_relevance_제로_길이(self):
        """길이 0 → 0으로 나누기 방지"""
        rel = _calculate_relevance(3, 0)
        self.assertGreater(rel, 0.0)
        self.assertLessEqual(rel, 1.0)


if __name__ == "__main__":
    unittest.main()
