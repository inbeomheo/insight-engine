"""
다음 콘텐츠 추천 큐 서비스 테스트
"""
import pytest
from services.next_content_queue_service import (
    recommend_next,
    ContentRecommendation,
    _calculate_impact,
    _determine_priority,
    _recommend_from_gaps,
    _recommend_from_dna,
)


# ── 공통 테스트 데이터 ──

SAMPLE_DNA = {
    'dominant_topics': ['인공지능', '머신러닝', '데이터분석'],
    'tone_profile': {'formal': 0.4, 'casual': 0.2, 'technical': 0.4},
    'avg_length': 1500.0,
    'keyword_fingerprint': ['인공지능', '머신러닝', '데이터', '분석', '기술'],
    'content_type_distribution': {'blog': 0.6, 'tutorial': 0.3, 'summary': 0.1},
}

CASUAL_DNA = {
    'dominant_topics': ['마케팅', '브랜딩'],
    'tone_profile': {'formal': 0.1, 'casual': 0.7, 'technical': 0.2},
    'avg_length': 800.0,
    'keyword_fingerprint': ['마케팅', '브랜딩', '고객'],
    'content_type_distribution': {'blog': 0.8, 'sns_post': 0.2},
}


class TestCalculateImpact:
    """영향도 계산 테스트"""

    def test_gap_bonus(self):
        impact_gap = _calculate_impact('새주제', 'blog', is_gap=True, dna=SAMPLE_DNA)
        impact_no_gap = _calculate_impact('새주제', 'blog', is_gap=False, dna=SAMPLE_DNA)
        assert impact_gap > impact_no_gap

    def test_new_topic_bonus(self):
        # '블록체인'은 DNA에 없는 새 주제
        impact_new = _calculate_impact('블록체인', 'blog', is_gap=False, dna=SAMPLE_DNA)
        # '인공지능'은 DNA에 있는 기존 주제
        impact_existing = _calculate_impact('인공지능', 'blog', is_gap=False, dna=SAMPLE_DNA)
        assert impact_new > impact_existing

    def test_underrepresented_type_bonus(self):
        # 'qna'는 분포에 없음 → 가산
        impact_missing = _calculate_impact('주제', 'qna', is_gap=False, dna=SAMPLE_DNA)
        # 'blog'는 0.6으로 충분 → 가산 없음
        impact_present = _calculate_impact('주제', 'blog', is_gap=False, dna=SAMPLE_DNA)
        assert impact_missing >= impact_present

    def test_impact_capped_at_one(self):
        # 모든 보너스가 적용되어도 1.0을 초과하지 않아야 함
        impact = _calculate_impact('완전새주제', 'tutorial', is_gap=True, dna=SAMPLE_DNA)
        assert impact <= 1.0

    def test_impact_minimum(self):
        impact = _calculate_impact('주제', 'unknown_type', is_gap=False, dna=SAMPLE_DNA)
        assert impact >= 0.0

    def test_known_type_weight(self):
        impact_tutorial = _calculate_impact('주제', 'tutorial', is_gap=False, dna={'dominant_topics': ['주제'], 'content_type_distribution': {'tutorial': 0.5}})
        impact_sns = _calculate_impact('주제', 'sns_post', is_gap=False, dna={'dominant_topics': ['주제'], 'content_type_distribution': {'sns_post': 0.5}})
        # tutorial(0.9) > sns_post(0.5)
        assert impact_tutorial > impact_sns


class TestDeterminePriority:
    """우선순위 결정 테스트"""

    def test_high_priority(self):
        assert _determine_priority(0.9) == 'high'
        assert _determine_priority(0.8) == 'high'

    def test_medium_priority(self):
        assert _determine_priority(0.7) == 'medium'
        assert _determine_priority(0.6) == 'medium'

    def test_low_priority(self):
        assert _determine_priority(0.5) == 'low'
        assert _determine_priority(0.3) == 'low'
        assert _determine_priority(0.0) == 'low'


class TestRecommendFromGaps:
    """갭 기반 추천 테스트"""

    def test_basic_gap_recommendations(self):
        gaps = ['블록체인', '클라우드']
        recs = _recommend_from_gaps(SAMPLE_DNA, gaps)
        assert len(recs) == 2
        topics = [r.topic for r in recs]
        assert '블록체인' in topics
        assert '클라우드' in topics

    def test_gap_priority_is_high(self):
        gaps = ['중요한주제']
        recs = _recommend_from_gaps(SAMPLE_DNA, gaps)
        assert len(recs) > 0
        # 갭 기반 추천은 보너스가 있어 priority가 medium 이상
        assert recs[0].priority in ('high', 'medium')

    def test_gap_reason_contains_topic(self):
        gaps = ['보안']
        recs = _recommend_from_gaps(SAMPLE_DNA, gaps)
        assert len(recs) == 1
        assert '보안' in recs[0].reason

    def test_empty_gaps(self):
        recs = _recommend_from_gaps(SAMPLE_DNA, [])
        assert recs == []

    def test_whitespace_gaps_filtered(self):
        gaps = ['', '  ', '유효한주제']
        recs = _recommend_from_gaps(SAMPLE_DNA, gaps)
        assert len(recs) == 1
        assert recs[0].topic == '유효한주제'


class TestRecommendFromDNA:
    """DNA 기반 추천 테스트"""

    def test_basic_dna_recommendations(self):
        recs = _recommend_from_dna(SAMPLE_DNA, set())
        assert len(recs) > 0

    def test_technical_tone_prefers_tutorial(self):
        tech_dna = {
            'dominant_topics': ['API설계'],
            'tone_profile': {'formal': 0.1, 'casual': 0.1, 'technical': 0.8},
            'content_type_distribution': {},
        }
        recs = _recommend_from_dna(tech_dna, set())
        # 기술 톤이 높으면 tutorial 추천
        topic_recs = [r for r in recs if r.topic == 'API설계' and r.content_type == 'tutorial']
        assert len(topic_recs) > 0

    def test_casual_tone_prefers_sns(self):
        recs = _recommend_from_dna(CASUAL_DNA, set())
        # 캐주얼 톤이 높으면 sns_post 추천
        sns_recs = [r for r in recs if r.content_type == 'sns_post']
        assert len(sns_recs) > 0

    def test_diversification_recommendations(self):
        # blog만 있는 DNA → 다른 유형 추천
        blog_only_dna = {
            'dominant_topics': ['테스트주제'],
            'tone_profile': {'formal': 0.5, 'casual': 0.3, 'technical': 0.2},
            'content_type_distribution': {'blog': 1.0},
        }
        recs = _recommend_from_dna(blog_only_dna, set())
        types = {r.content_type for r in recs}
        # blog 외 다른 유형이 추천되어야 함
        assert len(types) > 1

    def test_existing_topics_excluded(self):
        existing = {'인공지능', '머신러닝', '데이터분석'}
        recs = _recommend_from_dna(SAMPLE_DNA, existing)
        # 이미 존재하는 주제는 강점 심화 추천에서 제외
        topic_recs = [r for r in recs if r.topic.lower() in existing and r.reason.startswith('핵심')]
        assert len(topic_recs) == 0


class TestRecommendNext:
    """통합 추천 테스트"""

    def test_basic_recommendation(self):
        recs = recommend_next(SAMPLE_DNA)
        assert len(recs) > 0
        for rec in recs:
            assert isinstance(rec, ContentRecommendation)
            assert rec.topic != ""
            assert rec.content_type != ""
            assert rec.priority in ('high', 'medium', 'low')
            assert 0.0 <= rec.estimated_impact <= 1.0
            assert rec.reason != ""

    def test_gaps_prioritized(self):
        gaps = ['긴급주제']
        recs = recommend_next(SAMPLE_DNA, gaps=gaps)
        # 갭 주제가 결과에 포함되어야 함
        gap_topics = [r.topic for r in recs]
        assert '긴급주제' in gap_topics

    def test_sorted_by_priority_then_impact(self):
        recs = recommend_next(SAMPLE_DNA, gaps=['갭주제1', '갭주제2'])
        if len(recs) >= 2:
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            for i in range(len(recs) - 1):
                curr_p = priority_order.get(recs[i].priority, 3)
                next_p = priority_order.get(recs[i + 1].priority, 3)
                if curr_p == next_p:
                    # 같은 우선순위면 impact 내림차순
                    assert recs[i].estimated_impact >= recs[i + 1].estimated_impact
                else:
                    assert curr_p <= next_p

    def test_empty_dna(self):
        recs = recommend_next({})
        assert recs == []

    def test_none_dna(self):
        recs = recommend_next(None)
        assert recs == []

    def test_invalid_dna_type(self):
        recs = recommend_next("not a dict")
        assert recs == []

    def test_gaps_none(self):
        recs = recommend_next(SAMPLE_DNA, gaps=None)
        # gaps=None이면 DNA 기반만 추천
        assert len(recs) > 0

    def test_no_duplicate_topics(self):
        recs = recommend_next(SAMPLE_DNA, gaps=['인공지능'])
        # 같은 topic+content_type 조합이 중복되지 않아야 함
        seen = set()
        for rec in recs:
            key = (rec.topic, rec.content_type)
            assert key not in seen, f"중복 추천: {key}"
            seen.add(key)

    def test_recommendation_with_all_fields(self):
        recs = recommend_next(SAMPLE_DNA, gaps=['테스트갭'])
        for rec in recs:
            assert hasattr(rec, 'topic')
            assert hasattr(rec, 'content_type')
            assert hasattr(rec, 'priority')
            assert hasattr(rec, 'reason')
            assert hasattr(rec, 'estimated_impact')

    def test_gaps_with_empty_dna_topics(self):
        minimal_dna = {
            'dominant_topics': [],
            'tone_profile': {},
            'content_type_distribution': {},
        }
        recs = recommend_next(minimal_dna, gaps=['신규주제'])
        assert len(recs) >= 1
        assert recs[0].topic == '신규주제'
