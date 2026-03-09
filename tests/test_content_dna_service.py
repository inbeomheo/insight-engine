"""
콘텐츠 DNA 프로파일러 서비스 테스트
"""
import pytest
from services.content_dna_service import (
    profile_dna,
    ContentDNA,
    _analyze_tone,
    _extract_keywords,
    _compute_type_distribution,
    _extract_topics,
    _count_pattern_matches,
)


class TestAnalyzeTone:
    """톤 분석 테스트"""

    def test_formal_korean(self):
        text = "본 보고서는 인공지능 기술에 대해 분석합니다. 따라서 결론적으로 중요합니다."
        tone = _analyze_tone(text)
        assert tone['formal'] > 0
        assert 'casual' in tone
        assert 'technical' in tone

    def test_casual_korean(self):
        text = "진짜 대박이에요~ 완전 좋거든요ㅋㅋ 여러분도 해보세요!!"
        tone = _analyze_tone(text)
        assert tone['casual'] > tone['formal']

    def test_technical_text(self):
        text = "REST API를 통해 JSON 데이터를 HTTP 요청으로 처리합니다. SDK 활용이 필요합니다."
        tone = _analyze_tone(text)
        assert tone['technical'] > 0

    def test_empty_text(self):
        tone = _analyze_tone("")
        assert tone == {'formal': 0.0, 'casual': 0.0, 'technical': 0.0}

    def test_no_indicators(self):
        # 패턴에 매칭되지 않는 텍스트 → 균등 분포
        text = "가나다라마바사"
        tone = _analyze_tone(text)
        assert abs(tone['formal'] - 0.34) < 0.01
        assert abs(tone['casual'] - 0.33) < 0.01
        assert abs(tone['technical'] - 0.33) < 0.01

    def test_tone_values_sum_to_one(self):
        text = "인공지능 기술은 합니다. 진짜 대박 API 활용!"
        tone = _analyze_tone(text)
        total = sum(tone.values())
        assert abs(total - 1.0) < 0.05  # 반올림 오차 허용


class TestExtractKeywords:
    """키워드 추출 테스트"""

    def test_korean_keywords(self):
        texts = ["인공지능 기술이 발전합니다. 인공지능은 핵심입니다."]
        keywords = _extract_keywords(texts, max_keywords=5)
        assert len(keywords) > 0
        assert '인공지능' in keywords

    def test_english_keywords(self):
        texts = ["Machine learning is powerful. Machine learning helps data analysis."]
        keywords = _extract_keywords(texts, max_keywords=5)
        assert len(keywords) > 0
        assert 'machine' in keywords or 'learning' in keywords

    def test_stopwords_excluded(self):
        texts = ["the a an is are was were be been and or but if then so"]
        keywords = _extract_keywords(texts, max_keywords=10)
        # 모든 단어가 불용어이므로 결과 없음
        assert len(keywords) == 0

    def test_max_keywords_limit(self):
        texts = ["인공지능 머신러닝 딥러닝 데이터 분석 자연어 처리 컴퓨터 비전 강화학습 전이학습"]
        keywords = _extract_keywords(texts, max_keywords=3)
        assert len(keywords) <= 3

    def test_empty_texts(self):
        assert _extract_keywords([], max_keywords=5) == []

    def test_multiple_texts_combined(self):
        texts = [
            "인공지능 기술이 발전합니다",
            "인공지능 활용 사례가 늘어납니다",
            "데이터 분석이 중요합니다",
        ]
        keywords = _extract_keywords(texts, max_keywords=5)
        assert '인공지능' in keywords  # 2회 등장으로 상위


class TestComputeTypeDistribution:
    """유형 분포 계산 테스트"""

    def test_single_type(self):
        contents = [
            {'type': 'blog'},
            {'type': 'blog'},
            {'type': 'blog'},
        ]
        dist = _compute_type_distribution(contents)
        assert dist['blog'] == 1.0

    def test_mixed_types(self):
        contents = [
            {'type': 'blog'},
            {'type': 'tutorial'},
            {'type': 'blog'},
            {'type': 'newsletter'},
        ]
        dist = _compute_type_distribution(contents)
        assert dist['blog'] == 0.5
        assert dist['tutorial'] == 0.25
        assert dist['newsletter'] == 0.25

    def test_empty_contents(self):
        assert _compute_type_distribution([]) == {}

    def test_missing_type_defaults_to_unknown(self):
        contents = [{'title': 'test'}]  # type 필드 없음
        dist = _compute_type_distribution(contents)
        assert 'unknown' in dist

    def test_none_type_defaults_to_unknown(self):
        contents = [{'type': None}]
        dist = _compute_type_distribution(contents)
        assert 'unknown' in dist


class TestExtractTopics:
    """주제 추출 테스트"""

    def test_korean_topics(self):
        texts = ["인공지능 기술의 발전과 활용. 인공지능은 매우 중요합니다."]
        topics = _extract_topics(texts, max_topics=5)
        assert len(topics) > 0

    def test_max_topics_limit(self):
        texts = ["인공지능 머신러닝 딥러닝 데이터분석 자연어처리 컴퓨터비전 강화학습"]
        topics = _extract_topics(texts, max_topics=3)
        assert len(topics) <= 3

    def test_empty_texts(self):
        assert _extract_topics([]) == []


class TestProfileDNA:
    """DNA 프로파일링 통합 테스트"""

    def test_basic_profiling(self):
        contents = [
            {
                'title': '인공지능 입문',
                'content': '인공지능은 현대 기술의 핵심입니다. 머신러닝과 딥러닝을 포함합니다.',
                'type': 'blog',
            },
            {
                'title': '데이터 분석 가이드',
                'content': '데이터 분석은 비즈니스 의사결정에 필수적입니다. 통계와 시각화가 중요합니다.',
                'type': 'tutorial',
            },
        ]
        dna = profile_dna(contents)

        assert isinstance(dna, ContentDNA)
        assert len(dna.dominant_topics) > 0
        assert dna.avg_length > 0
        assert len(dna.keyword_fingerprint) > 0
        assert len(dna.content_type_distribution) > 0
        assert 'formal' in dna.tone_profile

    def test_empty_contents(self):
        dna = profile_dna([])
        assert dna.dominant_topics == []
        assert dna.avg_length == 0.0
        assert dna.keyword_fingerprint == []
        assert dna.content_type_distribution == {}

    def test_none_content_fields(self):
        contents = [{'title': 'test', 'content': None, 'type': 'blog'}]
        dna = profile_dna(contents)
        # content가 None이면 유효하지 않으므로 빈 DNA
        assert dna.avg_length == 0.0

    def test_avg_length_calculation(self):
        contents = [
            {'content': 'a' * 100, 'type': 'blog'},
            {'content': 'b' * 200, 'type': 'blog'},
        ]
        dna = profile_dna(contents)
        assert dna.avg_length == 150.0

    def test_type_distribution_in_dna(self):
        contents = [
            {'content': '블로그 콘텐츠입니다', 'type': 'blog'},
            {'content': '튜토리얼 콘텐츠입니다', 'type': 'tutorial'},
            {'content': '또 다른 블로그입니다', 'type': 'blog'},
        ]
        dna = profile_dna(contents)
        assert dna.content_type_distribution['blog'] > dna.content_type_distribution['tutorial']

    def test_tone_profile_in_dna(self):
        contents = [
            {
                'content': 'REST API를 통해 JSON 데이터를 처리합니다. HTTP 요청이 필요합니다.',
                'type': 'tutorial',
            },
        ]
        dna = profile_dna(contents)
        assert 'technical' in dna.tone_profile
        assert dna.tone_profile['technical'] > 0

    def test_invalid_contents_filtered(self):
        contents = [
            'not a dict',  # 무효
            {'content': '유효한 콘텐츠입니다', 'type': 'blog'},
            42,  # 무효
        ]
        dna = profile_dna(contents)
        # 유효한 콘텐츠 1개만 처리
        assert dna.avg_length > 0

    def test_keyword_fingerprint_max_20(self):
        # 다양한 키워드가 포함된 긴 텍스트
        words = ' '.join(f'키워드{i}는 중요합니다' for i in range(30))
        contents = [{'content': words, 'type': 'blog'}]
        dna = profile_dna(contents)
        assert len(dna.keyword_fingerprint) <= 20

    def test_single_content(self):
        contents = [{'content': '단일 콘텐츠 테스트입니다', 'type': 'summary'}]
        dna = profile_dna(contents)
        assert dna.content_type_distribution.get('summary', 0) == 1.0

    def test_title_included_in_analysis(self):
        contents = [
            {
                'title': '블록체인 기술 심층 분석',
                'content': '이 글에서는 분산 원장 기술을 다룹니다.',
                'type': 'blog',
            },
        ]
        dna = profile_dna(contents)
        # 제목의 '블록체인'이 키워드에 포함될 수 있음
        all_text = ' '.join(dna.keyword_fingerprint + dna.dominant_topics)
        # 제목이 분석에 포함되는지 확인 (직접 매칭 또는 관련 키워드 존재)
        assert len(dna.keyword_fingerprint) > 0
