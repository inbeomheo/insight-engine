"""freshness_monitor_service 단위 테스트"""
import unittest
from datetime import datetime, timezone, timedelta

from services.seo.freshness_monitor_service import (
    check_freshness,
    _score_time_decay,
    _find_date_references,
    _find_volatile_tech,
)


class TestCheckFreshness(unittest.TestCase):

    def test_empty_content(self):
        result = check_freshness('', '2025-01-01')
        self.assertEqual(result['status'], 'stale')
        self.assertEqual(result['freshness_score'], 0)

    def test_none_content(self):
        result = check_freshness(None, '2025-01-01')
        self.assertEqual(result['status'], 'stale')

    def test_fresh_content(self):
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        result = check_freshness('오늘 작성된 콘텐츠입니다. 최신 정보를 담고 있습니다.', today)
        self.assertEqual(result['status'], 'fresh')
        self.assertGreaterEqual(result['freshness_score'], 70)
        self.assertEqual(result['days_since_published'], 0)

    def test_old_content(self):
        old_date = (datetime.now(timezone.utc) - timedelta(days=400)).strftime('%Y-%m-%d')
        result = check_freshness(
            '2020년 데이터에 따르면 시장 점유율이 45%이며 ChatGPT API를 활용합니다.',
            old_date,
        )
        self.assertIn(result['status'], ('aging', 'stale'))
        self.assertGreater(result['days_since_published'], 300)

    def test_content_with_old_year(self):
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        result = check_freshness('2020년에 발표된 데이터에 따르면 시장 규모는 50억입니다.', today)
        # 2020년 참조가 있으므로 risk_factors에 포함
        risk_types = [rf['type'] for rf in result['risk_factors']]
        self.assertIn('outdated_date_reference', risk_types)

    def test_content_with_stats(self):
        old_date = (datetime.now(timezone.utc) - timedelta(days=200)).strftime('%Y-%m-%d')
        result = check_freshness('시장 점유율이 45%이고 성장률은 매년 20% 증가합니다.', old_date)
        risk_types = [rf['type'] for rf in result['risk_factors']]
        self.assertIn('outdated_statistics', risk_types)

    def test_content_with_tech_keywords(self):
        old_date = (datetime.now(timezone.utc) - timedelta(days=100)).strftime('%Y-%m-%d')
        result = check_freshness('ChatGPT와 Claude의 API를 활용한 LLM 개발 가이드', old_date)
        risk_types = [rf['type'] for rf in result['risk_factors']]
        self.assertIn('volatile_technology', risk_types)

    def test_refresh_suggestions_exist(self):
        old_date = (datetime.now(timezone.utc) - timedelta(days=400)).strftime('%Y-%m-%d')
        result = check_freshness('2020년 데이터 기반 분석', old_date)
        self.assertTrue(len(result['refresh_suggestions']) > 0)

    def test_invalid_date_fallback(self):
        result = check_freshness('콘텐츠', 'invalid-date')
        # invalid date면 현재로 fallback → fresh
        self.assertIn(result['status'], ('fresh', 'aging'))

    def test_score_bounded(self):
        result = check_freshness('콘텐츠', '2020-01-01')
        self.assertGreaterEqual(result['freshness_score'], 0)
        self.assertLessEqual(result['freshness_score'], 100)


class TestScoreTimeDecay(unittest.TestCase):

    def test_recent(self):
        self.assertEqual(_score_time_decay(0), 100)
        self.assertEqual(_score_time_decay(30), 100)

    def test_medium(self):
        self.assertEqual(_score_time_decay(60), 85)

    def test_old(self):
        self.assertEqual(_score_time_decay(200), 50)

    def test_very_old(self):
        self.assertEqual(_score_time_decay(800), 15)


class TestFindDateReferences(unittest.TestCase):

    def test_finds_old_year(self):
        refs = _find_date_references('2020년에 시작된 프로젝트')
        self.assertTrue(len(refs) > 0)
        self.assertEqual(refs[0]['type'] if 'type' in refs[0] else '', '')
        # severity 확인
        self.assertIn(refs[0]['severity'], ('high', 'medium', 'low'))

    def test_no_date_refs(self):
        refs = _find_date_references('날짜가 없는 일반 텍스트입니다.')
        self.assertEqual(len(refs), 0)


class TestFindVolatileTech(unittest.TestCase):

    def test_finds_tech(self):
        found = _find_volatile_tech('GPT-4와 Claude API를 활용')
        self.assertGreater(len(found), 0)

    def test_no_tech(self):
        found = _find_volatile_tech('맛있는 요리 레시피')
        self.assertEqual(len(found), 0)


if __name__ == '__main__':
    unittest.main()
