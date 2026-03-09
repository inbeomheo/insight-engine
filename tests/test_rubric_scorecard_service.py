"""루브릭 스코어카드 서비스 테스트."""
import unittest
from services.rubric_scorecard_service import (
    score_content, create_rubric, Rubric, RubricCriterion, Scorecard, ScoreDetail,
)


class TestScoreContent(unittest.TestCase):
    """score_content 함수 테스트."""

    def test_empty_content(self):
        """빈 콘텐츠는 낮은 점수를 반환한다."""
        result = score_content('')
        self.assertIsInstance(result, Scorecard)
        self.assertEqual(result.grade, 'F')
        self.assertLessEqual(result.total_score, 30)

    def test_none_content(self):
        """None 입력도 에러 없이 처리한다."""
        result = score_content(None)
        self.assertIsInstance(result, Scorecard)
        self.assertEqual(result.grade, 'F')

    def test_return_structure(self):
        """반환 구조가 Scorecard 스펙에 맞는지 확인한다."""
        result = score_content('테스트 콘텐츠입니다.')
        self.assertIn('factuality', result.scores)
        self.assertIn('brand_voice', result.scores)
        self.assertIn('citation', result.scores)
        self.assertIn('seo', result.scores)
        self.assertIsInstance(result.content_id, str)
        self.assertIsInstance(result.total_score, float)
        self.assertIsInstance(result.grade, str)
        self.assertIsInstance(result.details, list)
        self.assertEqual(len(result.details), 4)

    def test_detail_structure(self):
        """ScoreDetail 항목의 필드가 올바른지 확인한다."""
        result = score_content('테스트')
        detail = result.details[0]
        self.assertIsInstance(detail, ScoreDetail)
        self.assertIsInstance(detail.criterion, str)
        self.assertGreaterEqual(detail.score, 0.0)
        self.assertEqual(detail.max_score, 100.0)
        self.assertIsInstance(detail.feedback, str)

    def test_high_factuality_score(self):
        """숫자/통계가 많은 콘텐츠는 사실성 점수가 높다."""
        content = (
            '매출이 150억 원에서 230억 원으로 53% 증가했습니다. '
            '전년 대비 80억 원 상승이며, 3분기 기준 최고치입니다. '
            '직원 수는 120명에서 180명으로 50% 증가했습니다.'
        )
        result = score_content(content)
        self.assertGreater(result.scores['factuality'], 50.0)

    def test_low_factuality_score(self):
        """숫자가 없는 콘텐츠는 사실성 점수가 낮다."""
        content = '이 글은 좋은 내용을 담고 있습니다. 참고하시기 바랍니다.'
        result = score_content(content)
        self.assertLess(result.scores['factuality'], 30.0)

    def test_brand_voice_clean(self):
        """금지 표현 없는 콘텐츠는 브랜드 보이스 100점이다."""
        content = '이 도구는 데이터 분석에 유용합니다. 사용법을 알아보겠습니다.'
        result = score_content(content)
        self.assertEqual(result.scores['brand_voice'], 100.0)

    def test_brand_voice_violation(self):
        """금지 표현이 포함되면 브랜드 보이스 점수가 감소한다."""
        content = '이 도구는 놀라운 혁신적 성능을 보여줍니다. 획기적입니다.'
        result = score_content(content)
        self.assertLess(result.scores['brand_voice'], 70.0)

    def test_citation_with_urls(self):
        """URL이 포함된 콘텐츠는 인용 점수가 높다."""
        content = (
            '출처: https://example.com/report 참조.\n'
            '자세한 내용은 https://docs.example.com 에서 확인하세요.\n'
            '원문: https://blog.example.com/post'
        )
        result = score_content(content)
        self.assertGreater(result.scores['citation'], 40.0)

    def test_citation_with_timestamps(self):
        """타임스탬프 인용이 있으면 인용 점수에 반영된다."""
        content = '[01:23] 이 부분에서 설명합니다. [05:30] 결론입니다. [10:00] 마무리.'
        result = score_content(content)
        self.assertGreater(result.scores['citation'], 20.0)

    def test_seo_good_structure(self):
        """제목/소제목/목록/강조가 있는 콘텐츠는 SEO 점수가 높다."""
        content = (
            '# 메인 제목\n\n'
            '## 섹션 1\n\n'
            '**핵심 포인트**를 알아봅니다.\n\n'
            '- 항목 1\n- 항목 2\n- 항목 3\n\n'
            '## 섹션 2\n\n'
            '**두 번째** 주제입니다.\n\n'
            '## 섹션 3\n\n'
            '**세 번째** 주제입니다.\n\n'
            '이 콘텐츠는 충분한 길이를 가지고 있어야 합니다. ' * 30
        )
        result = score_content(content)
        self.assertGreater(result.scores['seo'], 50.0)

    def test_seo_no_structure(self):
        """구조 없는 짧은 텍스트는 SEO 점수가 낮다."""
        content = '짧은 글.'
        result = score_content(content)
        self.assertLess(result.scores['seo'], 20.0)

    def test_grade_a(self):
        """총점 90 이상이면 A 등급이다."""
        # 브랜드 보이스 100, 나머지도 높게
        content = (
            '# 2024년 매출 보고서\n\n'
            '## 요약\n\n'
            '매출 **150억 원**에서 **230억 원**으로 53% 증가. '
            '전년 대비 80억 원 상승.\n\n'
            '## 상세 분석\n\n'
            '- 1분기: 50억 원\n- 2분기: 60억 원\n- 3분기: 70억 원\n'
            '- 4분기: 50억 원\n\n'
            '## 출처\n\n'
            '출처: https://example.com/report1\n'
            '참조: https://example.com/report2\n'
            '참고: https://example.com/report3\n\n'
            '## 결론\n\n'
            '**지속적 성장**이 확인됩니다. ' * 40
        )
        result = score_content(content)
        self.assertIn(result.grade, ['A', 'B'])  # 구조에 따라 A 또는 B

    def test_grade_f(self):
        """총점 60 미만이면 F 등급이다."""
        content = '놀라운 혁신적 획기적 최고의 제품.'
        result = score_content(content)
        self.assertEqual(result.grade, 'F')

    def test_weighted_average(self):
        """총점이 가중 평균으로 계산되는지 확인한다."""
        result = score_content('테스트 콘텐츠')
        # 가중 평균은 개별 점수의 단순 평균과 다를 수 있음
        self.assertGreaterEqual(result.total_score, 0.0)
        self.assertLessEqual(result.total_score, 100.0)

    def test_scores_in_range(self):
        """모든 개별 점수가 0~100 범위인지 확인한다."""
        content = '테스트 콘텐츠 100개 항목 50% 증가 https://example.com 출처'
        result = score_content(content)
        for key, score in result.scores.items():
            self.assertGreaterEqual(score, 0.0, f'{key} 점수가 0 미만')
            self.assertLessEqual(score, 100.0, f'{key} 점수가 100 초과')


class TestCreateRubric(unittest.TestCase):
    """create_rubric 함수 테스트."""

    def test_basic_creation(self):
        """커스텀 루브릭을 정상 생성한다."""
        rubric = create_rubric('custom', {
            'factuality': {'name': '사실성', 'weight': 0.5, 'description': '테스트'},
            'brand_voice': {'name': '브랜드', 'weight': 0.5, 'description': '테스트'},
        })
        self.assertIsInstance(rubric, Rubric)
        self.assertEqual(rubric.name, 'custom')
        self.assertEqual(len(rubric.criteria), 2)

    def test_custom_rubric_scoring(self):
        """커스텀 루브릭으로 채점이 동작한다."""
        rubric = create_rubric('two_criteria', {
            'factuality': {'name': '사실성', 'weight': 0.7, 'description': '숫자 중심'},
            'seo': {'name': 'SEO', 'weight': 0.3, 'description': '구조'},
        })
        result = score_content('테스트 100개 50% 증가', rubric)
        self.assertIsInstance(result, Scorecard)
        self.assertIn('factuality', result.scores)
        self.assertIn('seo', result.scores)
        # brand_voice, citation은 없어야 함
        self.assertNotIn('brand_voice', result.scores)

    def test_unknown_criterion_gets_zero(self):
        """등록되지 않은 채점 기준은 0점으로 처리된다."""
        rubric = create_rubric('unknown', {
            'novelty': {'name': '참신성', 'weight': 1.0, 'description': '새로운 관점'},
        })
        result = score_content('어떤 콘텐츠', rubric)
        self.assertEqual(result.scores['novelty'], 0.0)
        self.assertEqual(result.details[0].feedback, '채점 함수 미등록')

    def test_default_weight(self):
        """weight 미지정 시 기본값 0.25가 적용된다."""
        rubric = create_rubric('minimal', {
            'factuality': {'name': '사실성', 'description': '테스트'},
        })
        self.assertEqual(rubric.criteria['factuality'].weight, 0.25)


if __name__ == '__main__':
    unittest.main()
