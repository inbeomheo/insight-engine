"""콘텐츠 성과 예측 서비스 테스트."""

import unittest

from services.seo.content_performance_predictor_service import predict_performance


class TestContentPerformancePredictorService(unittest.TestCase):
    """predict_performance 함수 테스트."""

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본값 반환."""
        result = predict_performance("")
        self.assertEqual(result["overall_score"], 0.0)
        self.assertEqual(result["grade"], "F")
        self.assertEqual(result["prediction"], "low")
        self.assertEqual(len(result["strengths"]), 0)
        self.assertGreater(len(result["weaknesses"]), 0)

    def test_none_content(self):
        """None 입력 시 기본값 반환."""
        result = predict_performance(None)
        self.assertEqual(result["overall_score"], 0.0)
        self.assertEqual(result["grade"], "F")
        self.assertEqual(result["prediction"], "low")

    def test_basic_prediction(self):
        """기본 예측 결과 구조 검증."""
        result = predict_performance("이것은 테스트 콘텐츠입니다. 충분한 길이의 문장을 작성합니다.")
        # 필수 키 존재 여부
        self.assertIn("overall_score", result)
        self.assertIn("grade", result)
        self.assertIn("category_scores", result)
        self.assertIn("prediction", result)
        self.assertIn("strengths", result)
        self.assertIn("weaknesses", result)
        self.assertIn("suggestions", result)
        # 카테고리 키 존재 여부
        cats = result["category_scores"]
        for key in ["readability", "engagement", "seo_signals", "structure", "shareability"]:
            self.assertIn(key, cats)

    def test_score_range(self):
        """모든 점수가 0-100 범위 내인지 검증."""
        content = "여러분, 이 글이 중요한 이유를 아시나요? 반드시 확인하세요!"
        result = predict_performance(content, title="중요한 테스트 제목입니다")
        self.assertGreaterEqual(result["overall_score"], 0)
        self.assertLessEqual(result["overall_score"], 100)
        for score in result["category_scores"].values():
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

    def test_grade_mapping(self):
        """등급 매핑이 S/A/B/C/D/F 중 하나인지 검증."""
        valid_grades = {"S", "A", "B", "C", "D", "F"}
        # 다양한 콘텐츠로 등급 확인
        contents = [
            "",
            "짧은 글",
            "이것은 적당한 길이의 콘텐츠입니다. " * 20,
        ]
        for c in contents:
            result = predict_performance(c)
            self.assertIn(result["grade"], valid_grades)

    def test_high_quality_content(self):
        """고품질 콘텐츠는 높은 점수를 받아야 한다."""
        content = """## 생산성을 높이는 5가지 핵심 전략

여러분, 생산성을 높이고 싶으신가요? 이 글에서 반드시 알아야 할 핵심 전략을 소개합니다.

## 1. 시간 관리의 중요한 원칙

효과적인 시간 관리는 생산성의 기본입니다. 연구에 따르면 계획을 세운 사람은 그렇지 않은 사람보다 25% 더 높은 성과를 냅니다.

## 2. 집중력 향상 방법

"몰입은 최고의 생산성 도구다"라고 전문가들은 말합니다. 하루 3시간의 집중 작업이 8시간의 분산 작업보다 낫습니다.

## 3. 도구 활용하기

- 할 일 목록 앱 사용
- 포모도로 타이머 활용
- 방해 요소 차단 도구 설치

지금 바로 시작하세요! 이 전략들을 적용하면 생산성이 50% 향상될 수 있습니다.

더 자세한 내용이 궁금하신가요? 확인하세요!"""

        result = predict_performance(content, title="생산성을 높이는 5가지 핵심 전략")
        # 고품질 콘텐츠는 중간 이상
        self.assertGreaterEqual(result["overall_score"], 50)
        self.assertIn(result["prediction"], ["high", "medium"])

    def test_low_quality_content(self):
        """저품질 콘텐츠(짧고 구조 없음)는 낮은 점수를 받아야 한다."""
        content = "짧은 글"
        result = predict_performance(content)
        self.assertLess(result["overall_score"], 50)
        self.assertGreater(len(result["weaknesses"]), 0)

    def test_readability_scoring(self):
        """가독성 점수 계산 검증."""
        # 적절한 문장 길이와 단락 구조
        content = """첫 번째 단락입니다. 적절한 길이의 문장을 씁니다.

두 번째 단락입니다. 가독성을 높이려면 문장을 짧게 써야 합니다.

세 번째 단락입니다. 이렇게 단락을 나누면 읽기 쉬워집니다.""" * 3

        result = predict_performance(content)
        # 3개 이상 단락 + 적절한 문장 길이 → 기본 점수 이상
        self.assertGreater(result["category_scores"]["readability"], 0)

    def test_engagement_scoring(self):
        """참여도 점수 계산 검증."""
        # 질문, 감정어, CTA, 독자 호칭 모두 포함
        content = (
            "여러분, 이 정보가 왜 중요한지 아시나요? "
            "핵심 내용을 반드시 확인해야 합니다. "
            "효과적인 방법을 지금 바로 시작하세요! "
            "궁금한 점이 있으신가요?"
        )
        result = predict_performance(content)
        # 4가지 요소 모두 포함 → 높은 참여도
        self.assertGreaterEqual(result["category_scores"]["engagement"], 75)

    def test_seo_with_title(self):
        """제목 포함 시 SEO 점수 검증."""
        title = "파이썬 프로그래밍 입문 가이드"
        # 제목 키워드가 본문에 2회 이상 반복
        content = """## 파이썬 프로그래밍 시작하기

파이썬 프로그래밍은 초보자에게 적합한 언어입니다. 파이썬을 배우면 다양한 분야에서 활용할 수 있습니다.

## 파이썬 기초 문법

프로그래밍의 기본을 이해하면 파이썬을 더 쉽게 배울 수 있습니다."""

        result = predict_performance(content, title=title)
        # 제목 길이 적절 + 키워드 반복 + 헤딩 → SEO 점수 존재
        self.assertGreater(result["category_scores"]["seo_signals"], 0)

    def test_structure_scoring(self):
        """구조 점수 계산 검증."""
        content = """## 첫 번째 섹션

이것은 첫 번째 내용입니다.

## 두 번째 섹션

이것은 두 번째 내용입니다.

## 세 번째 섹션

- 항목 1
- 항목 2
- 항목 3"""

        result = predict_performance(content)
        # 헤딩 3개 + 목록 3개 + 단락 3개 이상 → 구조 점수 높음
        self.assertGreaterEqual(result["category_scores"]["structure"], 50)

    def test_shareability_with_data(self):
        """숫자/통계 포함 시 공유 가능성 점수 검증."""
        content = """조사에 따르면 사용자의 80%가 이 기능을 선호합니다.

"데이터 기반 의사결정이 중요하다"라고 전문가는 말합니다.

- 매출 30% 증가
- 비용 15% 절감
- 고객 만족도 25% 향상

총 1000만원의 비용 절감 효과가 있었습니다."""

        result = predict_performance(content)
        # 숫자 + 인용문 + 구체적 데이터 + 리스트 → 높은 공유 가능성
        self.assertGreaterEqual(result["category_scores"]["shareability"], 75)

    def test_strengths_weaknesses(self):
        """강점/약점 목록이 올바르게 생성되는지 검증."""
        # 참여도만 높고 나머지는 낮은 콘텐츠
        content = "여러분, 핵심 전략을 확인하세요! 중요한 내용이에요. 궁금하지 않으세요?"
        result = predict_performance(content)

        # 강점/약점은 리스트 타입
        self.assertIsInstance(result["strengths"], list)
        self.assertIsInstance(result["weaknesses"], list)

        # 약점이 있으면 한국어 설명 포함
        for w in result["weaknesses"]:
            self.assertIsInstance(w, str)
            self.assertIn("부족합니다", w)

    def test_suggestions_exist(self):
        """약점이 있을 때 제안 목록이 생성되는지 검증."""
        # 짧은 콘텐츠 → 약점 존재 → 제안 생성
        content = "짧은 테스트 글입니다."
        result = predict_performance(content)

        self.assertIsInstance(result["suggestions"], list)
        # 약점이 있으면 제안도 있어야 함
        if result["weaknesses"]:
            self.assertGreater(len(result["suggestions"]), 0)


if __name__ == "__main__":
    unittest.main()
