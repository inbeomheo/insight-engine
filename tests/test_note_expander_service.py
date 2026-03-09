"""note_expander_service 단위 테스트"""
import unittest

from services.note_expander_service import (
    expand_note,
    generate_upsell_ctas,
    ExpansionCandidate,
    _calculate_expansion_score,
    _generate_outline,
    _split_paragraphs,
)


class TestExpandNote(unittest.TestCase):
    """expand_note 함수 테스트"""

    def test_basic_expansion_candidate(self):
        """기본 노트 확장 판단"""
        result = expand_note("파이썬 웹 개발 방법 가이드")
        self.assertIsInstance(result, ExpansionCandidate)
        self.assertEqual(result.original_note, "파이썬 웹 개발 방법 가이드")

    def test_expandable_short_note(self):
        """확장 가능한 짧은 노트 (키워드 포함)"""
        result = expand_note("React와 Vue 프레임워크 비교 분석 가이드")
        self.assertTrue(result.should_expand)
        self.assertGreater(len(result.expanded_outline), 0)
        self.assertGreater(result.estimated_length, 0)

    def test_non_expandable_emoticon(self):
        """감탄사만 있는 노트는 확장 불가"""
        result = expand_note("ㅋㅋㅋㅋ")
        self.assertFalse(result.should_expand)

    def test_non_expandable_url(self):
        """URL만 있는 노트는 확장 불가"""
        result = expand_note("https://example.com/article")
        self.assertFalse(result.should_expand)

    def test_non_expandable_number(self):
        """숫자만 있는 노트는 확장 불가"""
        result = expand_note("12345")
        self.assertFalse(result.should_expand)

    def test_empty_note_raises(self):
        """빈 노트 시 ValueError 발생"""
        with self.assertRaises(ValueError):
            expand_note("")

    def test_none_note_raises(self):
        """None 노트 시 ValueError 발생"""
        with self.assertRaises(ValueError):
            expand_note(None)

    def test_performance_boosts_expansion(self):
        """높은 성과 데이터가 확장 판단에 긍정적 영향"""
        note = "파이썬 팁 모음"
        # 성과 없이
        result_no_perf = expand_note(note)
        # 높은 성과로
        result_with_perf = expand_note(note, performance={
            "views": 5000, "likes": 200, "comments": 30
        })
        # 성과가 있을 때 should_expand가 True여야 함
        self.assertTrue(result_with_perf.should_expand)

    def test_performance_low_engagement(self):
        """낮은 성과 데이터는 확장 점수에 큰 영향 없음"""
        result = expand_note("일상 메모", performance={"views": 10, "likes": 0})
        # 확장 불가는 아닐 수 있지만 점수가 낮을 것
        self.assertIsInstance(result, ExpansionCandidate)

    def test_question_note_expansion(self):
        """질문형 노트는 확장 가치 높음"""
        result = expand_note("어떻게 하면 생산성을 높일 수 있을까? 방법을 찾아보자")
        self.assertTrue(result.should_expand)

    def test_short_note_below_minimum(self):
        """최소 길이 미달 노트"""
        result = expand_note("안녕")
        self.assertFalse(result.should_expand)
        self.assertIn("짧습니다", result.reason)

    def test_outline_structure(self):
        """확장 아웃라인이 올바른 구조인지"""
        result = expand_note("Docker 컨테이너 사용 방법 완벽 가이드")
        if result.should_expand:
            self.assertIn("도입: 주제 소개 및 배경", result.expanded_outline)
            # 마지막은 결론
            self.assertTrue(
                any("결론" in item for item in result.expanded_outline)
            )

    def test_reason_contains_explanation(self):
        """판단 사유에 설명이 포함되는지"""
        result = expand_note("Python 데이터 분석 트렌드")
        self.assertTrue(len(result.reason) > 0)


class TestGenerateUpsellCtas(unittest.TestCase):
    """generate_upsell_ctas 함수 테스트"""

    def test_basic_cta_generation(self):
        """기본 CTA 생성"""
        content = (
            "파이썬 개발 환경 설정 방법을 알아보겠습니다.\n\n"
            "먼저 파이썬을 설치해야 합니다. "
            "공식 사이트에서 다운로드할 수 있습니다.\n\n"
            "다음으로 VS Code를 설치하고 설정합니다. "
            "이 도구는 생산성을 크게 높여줍니다.\n\n"
            "마지막으로 가상환경을 만들어 보겠습니다. "
            "pip install virtualenv로 설치해 보세요."
        )
        result = generate_upsell_ctas(content)
        self.assertGreaterEqual(len(result), 2)

    def test_minimum_two_ctas(self):
        """최소 2개의 CTA 반환 보장"""
        content = (
            "간단한 첫 문단입니다. 특별한 내용은 없습니다.\n\n"
            "두 번째 문단도 평범합니다. 일반적인 설명입니다."
        )
        result = generate_upsell_ctas(content)
        self.assertGreaterEqual(len(result), 2)

    def test_cta_structure(self):
        """CTA 결과의 구조 확인"""
        content = (
            "이 강좌에서 배우는 내용입니다.\n\n"
            "첫 번째 단계는 도구를 설치하는 것입니다. "
            "추천하는 소프트웨어를 사용해 보세요.\n\n"
            "마지막으로 프로젝트를 완성합니다."
        )
        result = generate_upsell_ctas(content)
        for cta in result:
            self.assertIn('position', cta)
            self.assertIn('cta_text', cta)
            self.assertIn('cta_type', cta)
            self.assertIn('confidence', cta)
            self.assertIsInstance(cta['position'], int)
            self.assertGreaterEqual(cta['confidence'], 0.0)
            self.assertLessEqual(cta['confidence'], 1.0)

    def test_confidence_range(self):
        """CTA 신뢰도가 0.0~1.0 범위"""
        content = (
            "프로그래밍 강의 소개입니다.\n\n"
            "이 도구를 설치해서 사용해 보세요. 생산성이 올라갑니다.\n\n"
            "제품 구매 페이지에서 할인을 받으세요."
        )
        result = generate_upsell_ctas(content)
        for cta in result:
            self.assertGreaterEqual(cta['confidence'], 0.0)
            self.assertLessEqual(cta['confidence'], 1.0)

    def test_empty_content_raises(self):
        """빈 콘텐츠 시 ValueError 발생"""
        with self.assertRaises(ValueError):
            generate_upsell_ctas("")

    def test_none_content_raises(self):
        """None 콘텐츠 시 ValueError 발생"""
        with self.assertRaises(ValueError):
            generate_upsell_ctas(None)

    def test_tool_keyword_detection(self):
        """도구/툴 키워드 감지"""
        content = (
            "개발에 필수적인 도구를 소개합니다.\n\n"
            "이 소프트웨어를 사용하면 작업이 훨씬 쉬워집니다. "
            "지금 설치해서 시작해 보세요.\n\n"
            "다양한 플러그인도 활용 가능합니다."
        )
        result = generate_upsell_ctas(content)
        tool_ctas = [c for c in result if c['cta_type'] == 'tool']
        self.assertGreater(len(tool_ctas), 0)

    def test_purchase_intent_boosts_confidence(self):
        """구매 의도 신호가 신뢰도를 높이는지"""
        content = (
            "기본 소개 문단입니다.\n\n"
            "이 제품을 강력히 추천합니다. "
            "꼭 필요한 도구입니다. 사용해 보세요. "
            "시간 절약에 매우 효과적입니다.\n\n"
            "마무리 정리입니다."
        )
        result = generate_upsell_ctas(content)
        # 구매 의도가 높은 문단의 CTA는 높은 confidence
        high_conf = [c for c in result if c['confidence'] >= 0.3]
        self.assertGreater(len(high_conf), 0)

    def test_sorted_by_confidence(self):
        """결과가 confidence 내림차순으로 정렬"""
        content = (
            "첫 번째 문단 소개입니다.\n\n"
            "두 번째 문단에서 도구를 설치해 보세요. 추천합니다.\n\n"
            "세 번째 문단은 일반 내용입니다.\n\n"
            "네 번째 문단에서 강좌를 등록하고 학습을 시작하세요."
        )
        result = generate_upsell_ctas(content)
        if len(result) >= 2:
            for i in range(len(result) - 1):
                self.assertGreaterEqual(
                    result[i]['confidence'],
                    result[i + 1]['confidence'],
                )


class TestCalculateExpansionScore(unittest.TestCase):
    """_calculate_expansion_score 함수 테스트"""

    def test_short_note_high_score(self):
        """짧은 노트 + 확장 키워드 = 높은 점수"""
        score = _calculate_expansion_score("방법 가이드", None)
        self.assertGreaterEqual(score, 3)

    def test_long_note_lower_score(self):
        """긴 노트는 상대적으로 낮은 점수"""
        long_note = "일반적인 내용입니다. " * 100
        score = _calculate_expansion_score(long_note, None)
        short_note = "비교 분석 팁"
        short_score = _calculate_expansion_score(short_note, None)
        self.assertGreater(short_score, score)

    def test_performance_bonus(self):
        """성과 데이터가 점수에 반영"""
        note = "간단한 메모"
        score_no_perf = _calculate_expansion_score(note, None)
        score_with_perf = _calculate_expansion_score(
            note, {"views": 5000, "likes": 100, "comments": 20}
        )
        self.assertGreater(score_with_perf, score_no_perf)


class TestGenerateOutline(unittest.TestCase):
    """_generate_outline 함수 테스트"""

    def test_howto_outline(self):
        """방법/가이드 주제 아웃라인"""
        outline = _generate_outline("파이썬 설치 방법")
        self.assertTrue(any("단계별" in item for item in outline))

    def test_comparison_outline(self):
        """비교/리뷰 주제 아웃라인"""
        outline = _generate_outline("React vs Vue 비교")
        self.assertTrue(any("비교" in item for item in outline))

    def test_default_outline(self):
        """기본 주제 아웃라인"""
        outline = _generate_outline("오늘의 일기")
        self.assertTrue(any("도입" in item for item in outline))
        self.assertTrue(any("결론" in item for item in outline))


class TestSplitParagraphs(unittest.TestCase):
    """_split_paragraphs 함수 테스트"""

    def test_double_newline_split(self):
        """빈 줄 기준 분리"""
        text = "첫 번째 문단입니다.\n\n두 번째 문단입니다."
        result = _split_paragraphs(text)
        self.assertEqual(len(result), 2)

    def test_short_paragraph_filtered(self):
        """짧은 문단(10자 미만)은 필터링"""
        text = "첫 번째 문단입니다 충분히 긴 내용.\n\n짧음\n\n세 번째 문단입니다 충분히 긴 내용."
        result = _split_paragraphs(text)
        for p in result:
            self.assertGreaterEqual(len(p), 10)


if __name__ == '__main__':
    unittest.main()
