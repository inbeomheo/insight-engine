"""
Section Intent Drift Detector 서비스

각 소제목(헤딩)이 약속한 주제에서 해당 섹션 본문이
벗어나는 지점을 탐지합니다.
마크다운 헤딩 기준으로 섹션을 분할하고,
TF 기반 키워드 분석으로 주제 이탈을 판정합니다.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# 한국어 불용어 (조사·어미·접속사·일반 동사)
_STOPWORDS = {
    # 어미·서술어
    '있습니다', '합니다', '입니다', '됩니다', '것입니다', '하였다', '있다',
    '하다', '되다', '않다', '없다', '같다', '보다', '주다', '받다',
    # 조사·접속
    '위해', '통해', '대한', '하는', '이는', '있는', '되는', '않는',
    '그리고', '또한', '그러나', '하지만', '따라서', '그래서', '즉',
    # 일반 동사·형용사
    '사용', '필요', '가능', '다양', '제공', '포함', '진행', '설명',
    '경우', '방법', '관련', '수행', '구현', '처리', '실행', '활용',
    '대해', '에서', '으로', '에는', '으며', '이며',
    # 관형사·부사
    '매우', '가장', '더욱', '특히', '아주', '정말', '모든', '각각',
}

# 한국어 조사 패턴
_PARTICLES = re.compile(
    r'(은|는|이|가|을|를|의|에|와|과|도|로|으로|에서|까지|부터|만|라|란)$'
)
_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_KO_WORD_RE = re.compile(r'[가-힣]{2,10}')
_EN_WORD_RE = re.compile(r'[A-Za-z]{2,}')


def detect_section_drift(content: str) -> dict:
    """콘텐츠의 섹션별 주제 이탈을 분석합니다.

    Args:
        content: 마크다운 형식의 콘텐츠

    Returns:
        {
            "sections": [
                {
                    "heading": str,
                    "heading_keywords": list,
                    "top_body_keywords": list,
                    "relevance_score": float,
                    "status": str,       # "on_topic" | "partial_drift" | "drifted"
                    "drift_keywords": list,
                }
            ],
            "overall_coherence": float,  # 0-100
            "drifted_sections": list[str],
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'sections': [],
            'overall_coherence': 100.0,
            'drifted_sections': [],
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 섹션 분할
    sections = _split_sections(content)

    if not sections:
        return {
            'sections': [],
            'overall_coherence': 100.0,
            'drifted_sections': [],
            'suggestions': ['마크다운 헤딩(#)이 없습니다. 소제목을 추가해 주세요.'],
        }

    # 각 섹션 분석
    analyzed = []
    for heading, body in sections:
        result = _analyze_section(heading, body)
        analyzed.append(result)

    # 전체 일관성 점수 (0-100)
    if analyzed:
        avg_relevance = sum(s['relevance_score'] for s in analyzed) / len(analyzed)
        overall_coherence = round(avg_relevance * 100, 1)
    else:
        overall_coherence = 100.0

    # 이탈 섹션 목록
    drifted_sections = [
        s['heading'] for s in analyzed if s['status'] == 'drifted'
    ]

    # 제안사항 생성
    suggestions = _generate_suggestions(analyzed, drifted_sections)

    return {
        'sections': analyzed,
        'overall_coherence': overall_coherence,
        'drifted_sections': drifted_sections,
        'suggestions': suggestions,
    }


def _split_sections(content: str) -> list:
    """마크다운 헤딩 기준으로 (heading, body) 쌍으로 분할합니다."""
    matches = list(_HEADING_PATTERN.finditer(content))

    if not matches:
        return []

    sections = []
    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        # 본문: 현재 헤딩 이후 ~ 다음 헤딩 이전
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        sections.append((heading, body))

    return sections


def _extract_keywords(text: str) -> list:
    """텍스트에서 키워드를 추출합니다 (불용어 제거, 조사 제거)."""
    # 한국어 단어 (2~10자)
    korean_words = _KO_WORD_RE.findall(text)
    # 영어 단어 (2자+)
    english_words = _EN_WORD_RE.findall(text)

    keywords = []

    for word in korean_words:
        # 조사 제거
        stem = _PARTICLES.sub('', word)
        if len(stem) >= 2 and stem not in _STOPWORDS:
            keywords.append(stem)

    for word in english_words:
        lower = word.lower()
        if len(lower) >= 2:
            keywords.append(lower)

    return keywords


def _get_keyword_freq(keywords: list) -> Counter:
    """키워드 빈도를 계산합니다."""
    return Counter(keywords)


def _analyze_section(heading: str, body: str) -> dict:
    """단일 섹션의 주제 이탈을 분석합니다."""
    # 헤딩 키워드 추출
    heading_keywords = _extract_keywords(heading)
    # 중복 제거하되 순서 유지
    heading_keywords = list(dict.fromkeys(heading_keywords))

    # 본문이 비어있으면 판정 불가 → on_topic 처리
    if not body.strip():
        return {
            'heading': heading,
            'heading_keywords': heading_keywords,
            'top_body_keywords': [],
            'relevance_score': 1.0,
            'status': 'on_topic',
            'drift_keywords': [],
        }

    # 본문 키워드 빈도 분석
    body_keywords = _extract_keywords(body)
    body_freq = _get_keyword_freq(body_keywords)

    # 상위 본문 키워드 (최대 10개)
    top_body = [kw for kw, _ in body_freq.most_common(10)]

    # relevance_score 계산: 헤딩 키워드가 본문에 얼마나 등장하는지
    if heading_keywords and body_keywords:
        total_body_count = len(body_keywords)
        heading_hit_count = sum(
            body_freq.get(hk, 0) for hk in heading_keywords
        )
        relevance_score = min(heading_hit_count / total_body_count * 5.0, 1.0)
    elif not heading_keywords:
        # 헤딩에서 키워드를 추출할 수 없으면 판정 불가
        relevance_score = 0.5
    else:
        relevance_score = 0.0

    relevance_score = round(relevance_score, 3)

    # 드리프트 판정
    if relevance_score < 0.3:
        status = 'drifted'
    elif relevance_score < 0.6:
        status = 'partial_drift'
    else:
        status = 'on_topic'

    # drift_keywords: 본문 상위 키워드 중 헤딩과 무관한 것
    heading_kw_set = set(heading_keywords)
    drift_keywords = [kw for kw in top_body if kw not in heading_kw_set]

    return {
        'heading': heading,
        'heading_keywords': heading_keywords,
        'top_body_keywords': top_body,
        'relevance_score': relevance_score,
        'status': status,
        'drift_keywords': drift_keywords,
    }


def _generate_suggestions(analyzed: list, drifted_sections: list) -> list:
    """분석 결과를 기반으로 개선 제안을 생성합니다."""
    suggestions = []

    if not analyzed:
        return ['분석할 섹션이 없습니다.']

    # 심각한 이탈 섹션
    for section in analyzed:
        if section['status'] == 'drifted':
            drift_kws = ', '.join(section['drift_keywords'][:3]) if section['drift_keywords'] else '(없음)'
            suggestions.append(
                f'"{section["heading"]}" 섹션이 주제에서 벗어났습니다. '
                f'본문에서 [{drift_kws}] 관련 내용이 주를 이루고 있습니다.'
            )

    # 부분 이탈 섹션
    partial_count = sum(1 for s in analyzed if s['status'] == 'partial_drift')
    if partial_count > 0:
        suggestions.append(
            f'{partial_count}개 섹션에서 부분적 주제 이탈이 감지되었습니다. '
            f'소제목과 본문의 연관성을 강화해 보세요.'
        )

    # 전체 일관성이 낮을 때
    if analyzed:
        avg = sum(s['relevance_score'] for s in analyzed) / len(analyzed)
        if avg < 0.5:
            suggestions.append(
                '전체적으로 소제목과 본문의 일관성이 낮습니다. '
                '각 섹션이 소제목의 주제에 집중하도록 구조를 재정비해 보세요.'
            )

    # 이탈이 없으면 긍정 피드백
    if not drifted_sections and partial_count == 0:
        suggestions.append('모든 섹션이 소제목의 주제를 잘 유지하고 있습니다.')

    return suggestions
