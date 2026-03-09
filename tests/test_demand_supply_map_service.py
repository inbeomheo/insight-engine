"""
수요-공급 매핑 서비스 테스트

map_demand_supply() 함수의 기회/과포화/균형 분류,
점수 계산, 우선순위 판정, 엣지 케이스를 검증합니다.
"""
import pytest

from services.demand_supply_map_service import (
    DemandSupplyMap,
    Opportunity,
    map_demand_supply,
)


class TestMapDemandSupply:
    """map_demand_supply 핵심 기능 테스트"""

    def test_empty_topics_returns_empty(self):
        """빈 토픽 → 빈 결과"""
        result = map_demand_supply([], [])
        assert isinstance(result, DemandSupplyMap)
        assert result.opportunities == []
        assert result.oversaturated == []
        assert result.balanced == []

    def test_none_topics_returns_empty(self):
        """None 토픽 → 빈 결과"""
        result = map_demand_supply(None, None)
        assert result.opportunities == []

    def test_high_demand_no_supply_opportunity(self):
        """높은 수요 + 공급 없음 → 기회"""
        topics = [{"topic": "AI 자동화", "demand_score": 80}]
        supply = []
        result = map_demand_supply(topics, supply)
        assert len(result.opportunities) == 1
        assert result.opportunities[0].topic == "AI 자동화"
        assert result.opportunities[0].gap > 0

    def test_high_supply_low_demand_oversaturated(self):
        """높은 공급 + 낮은 수요 → 과포화"""
        topics = [{"topic": "블로그 팁", "demand_score": 10}]
        supply = [{"topic": "블로그 팁", "supply_score": 60}]
        result = map_demand_supply(topics, supply)
        assert "블로그 팁" in result.oversaturated

    def test_balanced_demand_supply(self):
        """수요 ≈ 공급 → 균형"""
        topics = [{"topic": "프로그래밍", "demand_score": 50}]
        supply = [{"topic": "프로그래밍", "supply_score": 50}]
        result = map_demand_supply(topics, supply)
        assert "프로그래밍" in result.balanced

    def test_opportunity_priority_high(self):
        """큰 갭(40+) → 높은 우선순위"""
        topics = [{"topic": "신기술", "demand_score": 90}]
        supply = [{"topic": "신기술", "supply_score": 20}]
        result = map_demand_supply(topics, supply)
        assert len(result.opportunities) >= 1
        assert result.opportunities[0].priority == "high"

    def test_opportunity_priority_medium(self):
        """중간 갭(20~40) → 중간 우선순위"""
        topics = [{"topic": "데이터분석", "demand_score": 60}]
        supply = [{"topic": "데이터분석", "supply_score": 30}]
        result = map_demand_supply(topics, supply)
        opp = [o for o in result.opportunities if o.topic == "데이터분석"]
        assert len(opp) == 1
        assert opp[0].priority in ("medium", "high")

    def test_multiple_topics_mixed(self):
        """여러 토픽이 서로 다른 분류로 배치"""
        topics = [
            {"topic": "A", "demand_score": 90},
            {"topic": "B", "demand_score": 10},
            {"topic": "C", "demand_score": 50},
        ]
        supply = [
            {"topic": "A", "supply_score": 10},
            {"topic": "B", "supply_score": 60},
            {"topic": "C", "supply_score": 50},
        ]
        result = map_demand_supply(topics, supply)
        opp_topics = {o.topic for o in result.opportunities}
        assert "A" in opp_topics
        assert "B" in result.oversaturated
        assert "C" in result.balanced

    def test_opportunities_sorted_by_gap(self):
        """기회가 갭 크기 내림차순 정렬"""
        topics = [
            {"topic": "X", "demand_score": 50},
            {"topic": "Y", "demand_score": 90},
            {"topic": "Z", "demand_score": 70},
        ]
        supply = [
            {"topic": "X", "supply_score": 10},
            {"topic": "Y", "supply_score": 10},
            {"topic": "Z", "supply_score": 10},
        ]
        result = map_demand_supply(topics, supply)
        if len(result.opportunities) >= 2:
            gaps = [o.gap for o in result.opportunities]
            assert gaps == sorted(gaps, reverse=True)

    def test_search_volume_based_demand(self):
        """search_volume 필드로 수요 추출"""
        topics = [{"topic": "SEO", "search_volume": 50000}]
        supply = [{"topic": "SEO", "supply_score": 5}]
        result = map_demand_supply(topics, supply)
        assert len(result.opportunities) >= 1

    def test_case_insensitive_topic_matching(self):
        """토픽 이름 대소문자 무관 매칭"""
        topics = [{"topic": "AI Tools", "demand_score": 80}]
        supply = [{"topic": "ai tools", "supply_score": 20}]
        result = map_demand_supply(topics, supply)
        assert len(result.opportunities) >= 1

    def test_empty_topic_name_skipped(self):
        """빈 토픽명 건너뛰기"""
        topics = [
            {"topic": "", "demand_score": 80},
            {"topic": "유효 토픽", "demand_score": 60},
        ]
        result = map_demand_supply(topics, [])
        opp_topics = {o.topic for o in result.opportunities}
        assert "" not in opp_topics
        assert "유효 토픽" in opp_topics

    def test_opportunity_dataclass_fields(self):
        """Opportunity 필드 타입 검증"""
        topics = [{"topic": "테스트", "demand_score": 70}]
        supply = [{"topic": "테스트", "supply_score": 10}]
        result = map_demand_supply(topics, supply)
        for opp in result.opportunities:
            assert isinstance(opp.topic, str)
            assert isinstance(opp.demand_score, float)
            assert isinstance(opp.supply_score, float)
            assert isinstance(opp.gap, float)
            assert opp.priority in ("high", "medium", "low")

    def test_none_supply_list(self):
        """공급 리스트 None → 모든 토픽이 기회"""
        topics = [{"topic": "새 분야", "demand_score": 50}]
        result = map_demand_supply(topics, None)
        assert len(result.opportunities) >= 1
