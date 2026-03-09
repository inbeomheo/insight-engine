"""영향원 레이더 서비스 테스트 — 15개+ 테스트 케이스."""

import unittest
from services.influence_radar_service import (
    InfluenceSource,
    scan_hidden_sources,
    _normalize_topic,
    _extract_normalized_topics,
    _detect_demographic_key,
    _compute_relevance,
    _scan_communities,
    _scan_publications,
    _scan_platforms,
    _scan_trends,
    _scan_influencer_niches,
)


class TestNormalizeTopic(unittest.TestCase):
    """토픽 정규화 테스트"""

    def test_english_alias(self):
        """영어 별칭이 표준 키로 변환되는지 확인"""
        self.assertEqual(_normalize_topic("technology"), "tech")
        self.assertEqual(_normalize_topic("programming"), "tech")
        self.assertEqual(_normalize_topic("artificial intelligence"), "ai")

    def test_korean_alias(self):
        """한국어 별칭이 표준 키로 변환되는지 확인"""
        self.assertEqual(_normalize_topic("개발"), "tech")
        self.assertEqual(_normalize_topic("인공지능"), "ai")
        self.assertEqual(_normalize_topic("마케팅"), "marketing")

    def test_unknown_topic_passthrough(self):
        """알 수 없는 토픽은 소문자로 그대로 반환"""
        self.assertEqual(_normalize_topic("Quantum Physics"), "quantum physics")

    def test_whitespace_stripping(self):
        """앞뒤 공백이 제거되는지 확인"""
        self.assertEqual(_normalize_topic("  tech  "), "tech")


class TestExtractNormalizedTopics(unittest.TestCase):
    """토픽 리스트 정규화 테스트"""

    def test_deduplication(self):
        """중복 토픽이 제거되는지 확인"""
        result = _extract_normalized_topics(["tech", "technology", "programming"])
        self.assertEqual(result, ["tech"])

    def test_empty_strings_skipped(self):
        """빈 문자열이 건너뛰어지는지 확인"""
        result = _extract_normalized_topics(["tech", "", "  ", "ai"])
        self.assertEqual(result, ["tech", "ai"])

    def test_non_string_skipped(self):
        """문자열이 아닌 항목이 건너뛰어지는지 확인"""
        result = _extract_normalized_topics(["tech", 123, None, "ai"])
        self.assertEqual(result, ["tech", "ai"])


class TestDetectDemographicKey(unittest.TestCase):
    """인구통계 세대 감지 테스트"""

    def test_generation_string(self):
        """generation 필드로 세대 감지"""
        self.assertEqual(_detect_demographic_key({"generation": "gen_z"}), "gen_z")
        self.assertEqual(_detect_demographic_key({"generation": "millennial"}), "millennial")
        self.assertEqual(_detect_demographic_key({"generation": "gen_x"}), "gen_x")

    def test_age_range(self):
        """age_range 필드로 세대 추론"""
        self.assertEqual(_detect_demographic_key({"age_range": "18-24"}), "gen_z")
        self.assertEqual(_detect_demographic_key({"age_range": "30-40"}), "millennial")
        self.assertEqual(_detect_demographic_key({"age_range": "50-60"}), "gen_x")

    def test_age_number(self):
        """단일 나이 값으로 세대 추론"""
        self.assertEqual(_detect_demographic_key({"age": "22"}), "gen_z")
        self.assertEqual(_detect_demographic_key({"age": "35"}), "millennial")

    def test_empty_demographics(self):
        """빈 인구통계는 빈 문자열 반환"""
        self.assertEqual(_detect_demographic_key({}), "")
        self.assertEqual(_detect_demographic_key(None), "")


class TestComputeRelevance(unittest.TestCase):
    """관련도 계산 테스트"""

    def test_first_topic_highest(self):
        """첫 번째 토픽의 관련도가 가장 높음"""
        topics = ["tech", "ai", "design"]
        self.assertGreater(
            _compute_relevance("tech", topics),
            _compute_relevance("ai", topics),
        )

    def test_position_bonus(self):
        """position_bonus가 적용되는지 확인"""
        topics = ["tech"]
        base = _compute_relevance("tech", topics)
        with_bonus = _compute_relevance("tech", topics, position_bonus=0.1)
        self.assertGreater(with_bonus, base)

    def test_max_capped_at_1(self):
        """관련도가 1.0을 초과하지 않음"""
        topics = ["tech"]
        result = _compute_relevance("tech", topics, position_bonus=0.5)
        self.assertLessEqual(result, 1.0)


class TestScanCommunities(unittest.TestCase):
    """커뮤니티 스캔 테스트"""

    def test_tech_communities(self):
        """tech 토픽의 커뮤니티가 반환되는지 확인"""
        sources = _scan_communities(["tech"])
        self.assertGreater(len(sources), 0)
        self.assertTrue(all(s.source_type == "community" for s in sources))

    def test_no_duplicates(self):
        """중복 토픽 시 커뮤니티 중복 없음"""
        sources = _scan_communities(["tech", "tech"])
        names = [s.name for s in sources]
        self.assertEqual(len(names), len(set(names)))

    def test_unknown_topic_empty(self):
        """알 수 없는 토픽은 빈 리스트"""
        sources = _scan_communities(["unknown_topic_xyz"])
        self.assertEqual(sources, [])


class TestScanPublications(unittest.TestCase):
    """매체 스캔 테스트"""

    def test_ai_publications(self):
        """ai 토픽의 매체가 반환되는지 확인"""
        sources = _scan_publications(["ai"])
        self.assertGreater(len(sources), 0)
        self.assertTrue(all(s.source_type == "publication" for s in sources))


class TestScanPlatforms(unittest.TestCase):
    """플랫폼 스캔 테스트"""

    def test_known_platforms(self):
        """알려진 플랫폼의 도달 규모가 반영되는지 확인"""
        sources = _scan_platforms(["youtube", "twitter"])
        self.assertEqual(len(sources), 2)
        youtube_src = [s for s in sources if "youtube" in s.name.lower()][0]
        self.assertEqual(youtube_src.reach_estimate, 2_000_000_000)

    def test_unknown_platform_default_reach(self):
        """알 수 없는 플랫폼은 기본 도달 규모 사용"""
        sources = _scan_platforms(["some_new_platform"])
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].reach_estimate, 100_000)

    def test_empty_platform_skipped(self):
        """빈 문자열 플랫폼은 건너뜀"""
        sources = _scan_platforms(["youtube", "", "  "])
        self.assertEqual(len(sources), 1)


class TestScanTrends(unittest.TestCase):
    """트렌드 스캔 테스트"""

    def test_gen_z_trends(self):
        """gen_z 인구통계의 트렌드가 반환되는지 확인"""
        sources = _scan_trends({"generation": "gen_z"})
        self.assertGreater(len(sources), 0)
        self.assertTrue(all(s.source_type == "trend" for s in sources))

    def test_no_demographics_empty(self):
        """인구통계 없으면 빈 리스트"""
        sources = _scan_trends({})
        self.assertEqual(sources, [])


class TestScanInfluencerNiches(unittest.TestCase):
    """인플루언서 니치 스캔 테스트"""

    def test_tech_influencers(self):
        """tech 토픽의 인플루언서 니치가 반환되는지 확인"""
        sources = _scan_influencer_niches(["tech"], {})
        self.assertGreater(len(sources), 0)
        self.assertTrue(all(s.source_type == "influencer" for s in sources))

    def test_demographic_bonus(self):
        """인구통계 매칭 시 관련도 보너스"""
        without_demo = _scan_influencer_niches(["tech"], {})
        with_demo = _scan_influencer_niches(["tech"], {"generation": "gen_z"})
        # 인구통계 있을 때 관련도가 더 높거나 같음
        if without_demo and with_demo:
            self.assertGreaterEqual(with_demo[0].relevance, without_demo[0].relevance)


class TestScanHiddenSources(unittest.TestCase):
    """scan_hidden_sources 통합 테스트"""

    def test_minimum_5_sources(self):
        """최소 5개 영향원이 반환되는지 확인"""
        result = scan_hidden_sources({"topics": [], "demographics": {}, "platforms": []})
        self.assertGreaterEqual(len(result), 5)

    def test_rich_data_many_sources(self):
        """풍부한 데이터에서 다양한 유형의 영향원 발굴"""
        data = {
            "topics": ["tech", "ai", "marketing"],
            "demographics": {"generation": "millennial"},
            "platforms": ["youtube", "twitter"],
        }
        result = scan_hidden_sources(data)
        self.assertGreater(len(result), 5)

        # 다양한 source_type 존재
        types = {s.source_type for s in result}
        self.assertGreaterEqual(len(types), 3)

    def test_sorted_by_relevance_desc(self):
        """결과가 관련도 내림차순으로 정렬됨"""
        data = {
            "topics": ["tech", "ai"],
            "demographics": {"age": "30"},
            "platforms": ["youtube"],
        }
        result = scan_hidden_sources(data)
        relevances = [s.relevance for s in result]
        self.assertEqual(relevances, sorted(relevances, reverse=True))

    def test_none_raises_value_error(self):
        """None 입력 시 ValueError 발생"""
        with self.assertRaises(ValueError):
            scan_hidden_sources(None)

    def test_empty_dict(self):
        """빈 dict에서도 최소 5개 폴백 영향원 반환"""
        result = scan_hidden_sources({})
        self.assertGreaterEqual(len(result), 5)

    def test_dataclass_fields(self):
        """InfluenceSource 필드가 올바른 타입인지 확인"""
        data = {"topics": ["tech"], "demographics": {}, "platforms": []}
        result = scan_hidden_sources(data)
        for src in result:
            self.assertIsInstance(src.name, str)
            self.assertIn(src.source_type, ("community", "publication", "influencer", "platform", "trend"))
            self.assertGreaterEqual(src.relevance, 0.0)
            self.assertLessEqual(src.relevance, 1.0)
            self.assertIsInstance(src.reach_estimate, int)
            self.assertIsInstance(src.description, str)

    def test_korean_topics(self):
        """한국어 토픽이 정규화되어 처리되는지 확인"""
        data = {
            "topics": ["인공지능", "마케팅"],
            "demographics": {},
            "platforms": [],
        }
        result = scan_hidden_sources(data)
        self.assertGreaterEqual(len(result), 5)
        # AI + 마케팅 관련 커뮤니티/매체가 포함되어야 함
        names = [s.name for s in result]
        has_ai_related = any("AI" in n or "ML" in n or "Machine" in n for n in names)
        self.assertTrue(has_ai_related, f"AI 관련 영향원이 없음: {names}")

    def test_non_list_topics_handled(self):
        """topics가 리스트가 아닌 경우 안전 처리"""
        data = {"topics": "tech", "demographics": {}, "platforms": []}
        result = scan_hidden_sources(data)
        # 에러 없이 폴백 결과 반환
        self.assertGreaterEqual(len(result), 5)

    def test_no_duplicate_names(self):
        """결과에 중복 이름이 없는지 확인"""
        data = {
            "topics": ["tech", "programming", "coding"],  # 모두 tech로 정규화
            "demographics": {},
            "platforms": [],
        }
        result = scan_hidden_sources(data)
        names = [s.name for s in result]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
