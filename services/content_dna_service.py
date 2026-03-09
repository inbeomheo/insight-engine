"""
콘텐츠 DNA 프로파일러 서비스

콘텐츠 목록을 분석하여 주제 빈도, 톤 프로파일,
길이 통계, 키워드 지문, 유형 분포를 생성합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List
from collections import Counter


@dataclass
class ContentDNA:
    """콘텐츠 DNA 프로파일"""
    dominant_topics: List[str] = field(default_factory=list)      # 지배적 주제 목록
    tone_profile: Dict[str, float] = field(default_factory=dict)  # 톤 분포 {formal/casual/technical: 비율}
    avg_length: float = 0.0                                        # 평균 콘텐츠 길이 (글자수)
    keyword_fingerprint: List[str] = field(default_factory=list)   # 키워드 지문 (상위 20)
    content_type_distribution: Dict[str, float] = field(default_factory=dict)  # 유형 분포 비율


# ── 톤 감지 패턴 ──

_FORMAL_INDICATORS_KO = [
    re.compile(r'(?:합니다|입니다|습니다|됩니다|겠습니다|있습니다|없습니다)'),
    re.compile(r'(?:하였|되었|이루어졌|진행되었|수행되었)'),
    re.compile(r'(?:따라서|그러므로|결론적으로|요약하면|상기)'),
]

_FORMAL_INDICATORS_EN = [
    re.compile(r'\b(?:furthermore|moreover|consequently|therefore|hereby|thus|accordingly)\b', re.IGNORECASE),
    re.compile(r'\b(?:shall|hereby|whereas|notwithstanding|hereafter)\b', re.IGNORECASE),
    re.compile(r'\b(?:it is|one should|it has been)\b', re.IGNORECASE),
]

_CASUAL_INDICATORS_KO = [
    re.compile(r'(?:해요|에요|거든요|잖아요|네요|죠|ㅋㅋ|ㅎㅎ|!!|~)'),
    re.compile(r'(?:진짜|완전|대박|짱|꿀팁|개꿀|레알)'),
    re.compile(r'(?:여러분|친구들|자기야|얘들아)'),
]

_CASUAL_INDICATORS_EN = [
    re.compile(r'\b(?:gonna|wanna|gotta|kinda|sorta|y\'all|ain\'t)\b', re.IGNORECASE),
    re.compile(r'(?:!!|lol|haha|omg|btw|tbh|imo)', re.IGNORECASE),
    re.compile(r'\b(?:awesome|cool|crazy|insane|dude|guys|hey)\b', re.IGNORECASE),
]

_TECHNICAL_INDICATORS = [
    re.compile(r'\b(?:API|SDK|REST|HTTP|JSON|XML|SQL|CSS|HTML|JWT|OAuth)\b'),
    re.compile(r'\b(?:algorithm|latency|throughput|scalability|architecture)\b', re.IGNORECASE),
    re.compile(r'(?:알고리즘|아키텍처|데이터베이스|프레임워크|라이브러리|인프라)'),
    re.compile(r'```[\s\S]*?```'),  # 코드 블록
    re.compile(r'\b\d+(?:\.\d+)+\b'),  # 버전 번호 (1.2.3)
    re.compile(r'\b(?:function|class|def|import|export|return|const|let|var)\b'),
]

# ── 불용어 ──

_STOPWORDS = frozenset([
    # 한국어
    '그리고', '하지만', '그러나', '또한', '때문에', '그래서', '따라서',
    '이것', '저것', '그것', '여기', '거기', '이런', '그런', '저런',
    '있다', '없다', '하다', '되다', '것이다', '합니다', '입니다', '습니다',
    '에서', '으로', '부터', '까지', '대한', '통해', '위해', '관한',
    # 영어
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'and', 'or', 'but', 'if', 'then',
    'so', 'that', 'this', 'these', 'those', 'it', 'its', 'of', 'in',
    'to', 'for', 'with', 'on', 'at', 'by', 'from', 'as', 'not', 'no',
])


def _count_pattern_matches(text: str, patterns: list) -> int:
    """패턴 목록의 총 매치 수를 반환합니다."""
    total = 0
    for p in patterns:
        total += len(p.findall(text))
    return total


def _analyze_tone(text: str) -> Dict[str, float]:
    """텍스트의 톤 프로파일을 분석합니다.

    Returns:
        {formal, casual, technical} 비율 (합계 1.0)
    """
    if not text.strip():
        return {'formal': 0.0, 'casual': 0.0, 'technical': 0.0}

    formal_count = (
        _count_pattern_matches(text, _FORMAL_INDICATORS_KO)
        + _count_pattern_matches(text, _FORMAL_INDICATORS_EN)
    )
    casual_count = (
        _count_pattern_matches(text, _CASUAL_INDICATORS_KO)
        + _count_pattern_matches(text, _CASUAL_INDICATORS_EN)
    )
    technical_count = _count_pattern_matches(text, _TECHNICAL_INDICATORS)

    total = formal_count + casual_count + technical_count

    if total == 0:
        # 매칭 없으면 기본 균등 분포
        return {'formal': 0.34, 'casual': 0.33, 'technical': 0.33}

    return {
        'formal': round(formal_count / total, 2),
        'casual': round(casual_count / total, 2),
        'technical': round(technical_count / total, 2),
    }


def _extract_keywords(texts: List[str], max_keywords: int = 20) -> List[str]:
    """콘텐츠 목록에서 키워드 지문을 추출합니다.

    빈도 기반 상위 키워드를 반환합니다.
    """
    all_words: List[str] = []

    for text in texts:
        # 한국어 2~8자 단어
        ko_words = re.findall(r'[가-힣]{2,8}', text)
        all_words.extend(ko_words)

        # 영어 3자 이상 단어 (소문자)
        en_words = re.findall(r'[a-zA-Z]{3,}', text)
        all_words.extend(w.lower() for w in en_words)

    # 불용어 제거
    filtered = [w for w in all_words if w.lower() not in _STOPWORDS]

    if not filtered:
        return []

    counter = Counter(filtered)
    return [word for word, _ in counter.most_common(max_keywords)]


def _compute_type_distribution(contents: List[Dict]) -> Dict[str, float]:
    """콘텐츠 유형별 분포를 계산합니다.

    Args:
        contents: [{"type": "blog"}, ...] 형태의 콘텐츠 목록

    Returns:
        {유형: 비율} (합계 1.0)
    """
    if not contents:
        return {}

    type_counter: Counter = Counter()
    for item in contents:
        content_type = item.get('type', 'unknown')
        if not content_type or not isinstance(content_type, str):
            content_type = 'unknown'
        type_counter[content_type] += 1

    total = sum(type_counter.values())
    return {t: round(c / total, 2) for t, c in type_counter.most_common()}


def _extract_topics(texts: List[str], max_topics: int = 10) -> List[str]:
    """콘텐츠 목록에서 지배적 주제를 추출합니다.

    키워드 클러스터링 없이 빈도 기반 상위 주제를 반환합니다.
    일반 키워드보다 긴 구문(2~4단어)을 우선합니다.
    """
    phrase_counter: Counter = Counter()

    for text in texts:
        # 한국어 복합 명사구 (3~10자)
        ko_phrases = re.findall(r'[가-힣]{3,10}', text)
        phrase_counter.update(ko_phrases)

        # 영어 2~3단어 구문
        en_phrases = re.findall(
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b', text
        )
        phrase_counter.update(p.lower() for p in en_phrases)

    # 불용어 필터링
    filtered = {
        phrase: count
        for phrase, count in phrase_counter.items()
        if phrase.lower() not in _STOPWORDS and count >= 1
    }

    if not filtered:
        return []

    sorted_phrases = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
    return [phrase for phrase, _ in sorted_phrases[:max_topics]]


def profile_dna(contents: List[Dict]) -> ContentDNA:
    """콘텐츠 목록의 DNA 프로파일을 생성합니다.

    Args:
        contents: [{"title": "...", "content": "...", "type": "blog"}, ...]

    Returns:
        ContentDNA 프로파일
    """
    if not contents:
        return ContentDNA()

    # 유효한 콘텐츠만 필터링
    valid_contents = [
        c for c in contents
        if isinstance(c, dict) and c.get('content')
    ]

    if not valid_contents:
        return ContentDNA()

    # 모든 텍스트 수집 (제목 + 본문)
    all_texts = []
    lengths = []

    for item in valid_contents:
        content_text = item.get('content', '')
        title_text = item.get('title', '')
        combined = f"{title_text} {content_text}".strip()
        all_texts.append(combined)
        lengths.append(len(content_text))

    # 1. 지배적 주제 추출
    dominant_topics = _extract_topics(all_texts)

    # 2. 톤 프로파일 (전체 텍스트 합산)
    combined_text = ' '.join(all_texts)
    tone_profile = _analyze_tone(combined_text)

    # 3. 평균 길이
    avg_length = round(sum(lengths) / len(lengths), 1) if lengths else 0.0

    # 4. 키워드 지문
    keyword_fingerprint = _extract_keywords(all_texts)

    # 5. 유형 분포
    content_type_distribution = _compute_type_distribution(valid_contents)

    return ContentDNA(
        dominant_topics=dominant_topics,
        tone_profile=tone_profile,
        avg_length=avg_length,
        keyword_fingerprint=keyword_fingerprint,
        content_type_distribution=content_type_distribution,
    )
