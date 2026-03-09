"""
콘텐츠 건강도 서비스 테스트

compute_health_score, HealthReport 검증.
"""
import unittest
from services.content_health_service import (
    HealthReport,
    compute_health_score,
)


class TestComputeHealthScoreEmpty(unittest.TestCase):
    """빈/무효 콘텐츠 처리"""

    def test_empty_string(self):
        """빈 문자열 → 0점, orphan 100"""
        report = compute_health_score('')
        self.assertEqual(report.overall_score, 0.0)
        self.assertEqual(report.freshness_score, 0.0)
        self.assertEqual(report.completeness_score, 0.0)
        self.assertEqual(report.orphan_risk, 100.0)
        self.assertIn('콘텐츠가 비어 있습니다.', report.recommendations)

    def test_none_content(self):
        """None → 빈 콘텐츠와 동일 처리"""
        report = compute_health_score(None)
        self.assertEqual(report.overall_score, 0.0)

    def test_whitespace_only(self):
        """공백만 → 빈 콘텐츠"""
        report = compute_health_score('   \n\t  ')
        self.assertEqual(report.overall_score, 0.0)


class TestHealthReportDataclass(unittest.TestCase):
    """HealthReport 데이터클래스 구조"""

    def test_report_fields(self):
        """필수 필드 존재 확인"""
        report = compute_health_score('테스트 콘텐츠입니다.')
        self.assertIsInstance(report, HealthReport)
        self.assertIsInstance(report.overall_score, float)
        self.assertIsInstance(report.freshness_score, float)
        self.assertIsInstance(report.completeness_score, float)
        self.assertIsInstance(report.orphan_risk, float)
        self.assertIsInstance(report.recommendations, list)


class TestFreshness(unittest.TestCase):
    """신선도 점수 검증"""

    def test_no_time_refs_high_freshness(self):
        """시간 참조 없으면 높은 신선도"""
        content = (
            '## 좋은 코드 작성법\n\n'
            '변수 이름은 의미를 담아야 합니다. '
            '함수는 [하나의 역할](https://example.com)만 수행해야 합니다. '
            '- 들여쓰기를 일관되게 하세요.\n'
            '- 주석은 "왜"를 설명하세요.\n'
            '코드 리뷰를 생활화합시다.'
        )
        report = compute_health_score(content)
        self.assertGreaterEqual(report.freshness_score, 80.0)

    def test_many_dates_low_freshness(self):
        """날짜 참조 많으면 낮은 신선도"""
        content = (
            '2024년 1월 보고서. 2024년 3월 업데이트. '
            '2023년 대비 변화. 2025년 전망. '
            '올해 목표. 작년 실적.'
        )
        report = compute_health_score(content)
        self.assertLessEqual(report.freshness_score, 60.0)

    def test_metadata_days_since_update(self):
        """metadata에 days_since_update → 추가 감점"""
        content = '## 가이드\n\n일반적인 내용입니다.'
        report_fresh = compute_health_score(content, metadata={'days_since_update': 30})
        report_stale = compute_health_score(content, metadata={'days_since_update': 400})
        self.assertGreater(report_fresh.freshness_score, report_stale.freshness_score)


class TestCompleteness(unittest.TestCase):
    """완성도 점수 검증"""

    def test_well_structured_high_completeness(self):
        """헤딩+리스트+링크 있는 콘텐츠 → 높은 완성도"""
        content = (
            '## 시작하기\n\n'
            '이 가이드는 초보자를 위한 안내입니다. '
            '다음 단계를 따라 진행하세요.\n\n'
            '- 첫 번째 단계: 환경 설정\n'
            '- 두 번째 단계: 프로젝트 생성\n'
            '- 세 번째 단계: 코드 작성\n\n'
            '## 참고 자료\n\n'
            '자세한 내용은 [공식 문서](https://docs.example.com)를 참조하세요. '
            '추가적으로 **핵심 개념**을 이해하는 것이 중요합니다.'
        )
        report = compute_health_score(content)
        self.assertGreaterEqual(report.completeness_score, 70.0)

    def test_short_content_low_completeness(self):
        """짧은 콘텐츠 → 낮은 완성도"""
        report = compute_health_score('짧은 글.')
        self.assertLessEqual(report.completeness_score, 70.0)

    def test_placeholder_detection(self):
        """TODO/TBD 플레이스홀더 → 감점"""
        content = (
            '## 프로젝트 구조\n\n'
            '이 프로젝트는 다음과 같이 구성됩니다.\n\n'
            'TODO: 나머지 내용 추가\n'
            'TBD: 아키텍처 설명 미정\n'
            '추후 작성 예정입니다.'
        )
        report = compute_health_score(content)
        # 플레이스홀더 감지 추천이 있어야 함
        has_placeholder_rec = any(
            'TODO' in r or 'TBD' in r or '미완성' in r
            for r in report.recommendations
        )
        self.assertTrue(has_placeholder_rec)

    def test_no_heading_long_content(self):
        """긴 콘텐츠에 헤딩 없으면 감점"""
        content = '좋은 코드를 작성하는 방법을 알아봅시다. ' * 50
        report = compute_health_score(content)
        has_heading_rec = any('헤딩' in r for r in report.recommendations)
        self.assertTrue(has_heading_rec)


class TestOrphanRisk(unittest.TestCase):
    """고아 위험 점수 검증"""

    def test_no_links_high_risk(self):
        """링크 없는 콘텐츠 → 높은 고아 위험"""
        content = '이 글은 독립적입니다. 다른 곳과 연결되지 않습니다.'
        report = compute_health_score(content)
        self.assertGreaterEqual(report.orphan_risk, 30.0)

    def test_with_links_lower_risk(self):
        """링크 있는 콘텐츠 → 낮은 고아 위험"""
        content = (
            '## 관련 문서\n\n'
            '- [가이드 A](https://a.com)를 먼저 읽으세요.\n'
            '- [가이드 B](https://b.com)도 참고하세요.\n'
            '- [가이드 C](https://c.com)와 연계됩니다.\n'
            '이 문서는 위 가이드들의 후속편입니다. ' * 10
        )
        report = compute_health_score(content)
        # 링크 3개 + 헤딩 있음 → 낮은 위험
        self.assertLessEqual(report.orphan_risk, 50.0)

    def test_metadata_incoming_links(self):
        """metadata의 incoming_links 활용"""
        content = '## 테스트\n\n내용입니다. ' * 20
        report_zero = compute_health_score(content, metadata={'incoming_links': 0})
        report_many = compute_health_score(content, metadata={'incoming_links': 10})
        self.assertGreater(report_zero.orphan_risk, report_many.orphan_risk)


class TestOverallScore(unittest.TestCase):
    """종합 점수 검증"""

    def test_score_range_0_to_100(self):
        """모든 점수가 0~100 범위"""
        cases = [
            '',
            '짧은 글',
            '## 제목\n\n' + '정상 콘텐츠입니다. ' * 100,
            '2024년 TODO TBD ' * 50,
        ]
        for content in cases:
            report = compute_health_score(content)
            for attr in ['overall_score', 'freshness_score', 'completeness_score', 'orphan_risk']:
                value = getattr(report, attr)
                self.assertGreaterEqual(value, 0.0, f'{attr} < 0 for content: {content[:30]}')
                self.assertLessEqual(value, 100.0, f'{attr} > 100 for content: {content[:30]}')

    def test_good_content_high_overall(self):
        """잘 구성된 콘텐츠 → 높은 종합 점수"""
        content = (
            '## 효과적인 시간 관리\n\n'
            '시간 관리는 생산성의 핵심입니다. '
            '다음 방법을 시도해보세요.\n\n'
            '- **우선순위 설정**: 중요한 일부터 처리하세요\n'
            '- **타임 블로킹**: 시간대별 작업 배정\n'
            '- **포모도로 기법**: 25분 집중, 5분 휴식\n\n'
            '## 실천 방법\n\n'
            '매일 아침 [계획 템플릿](https://example.com/template)을 활용하세요. '
            '자세한 내용은 [생산성 가이드](https://example.com/guide)를 참조하세요. '
            '꾸준한 실천이 가장 중요합니다.'
        )
        report = compute_health_score(content)
        self.assertGreaterEqual(report.overall_score, 60.0)

    def test_recommendations_list(self):
        """추천사항이 list[str]"""
        report = compute_health_score('짧은 글')
        self.assertIsInstance(report.recommendations, list)
        for rec in report.recommendations:
            self.assertIsInstance(rec, str)


if __name__ == '__main__':
    unittest.main()
