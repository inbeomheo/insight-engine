"""
소셜 프루프 스니펫 추출 서비스

콘텐츠에서 소셜 미디어 공유에 적합한 증거/인용/통계 스니펫을 추출합니다.
숫자, 인용문, 핵심 주장, before/after 등을 감지합니다.
"""
import re
import logging


logger = logging.getLogger(__name__)

# 스니펫 유형별 패턴
_STAT_PATTERN = re.compile(r'[^.!?。]*\d+[%％만억배원달러건명개][^.!?。]*[.!?。]?')
_QUOTE_PATTERN = re.compile(r'["\u201C\u201D\u300C\u300D]([^"\u201C\u201D\u300C\u300D]{10,80})["\u201C\u201D\u300C\u300D]')
_COMPARISON_PATTERN = re.compile(r'[^.!?。]*(비교|대비|vs|차이|보다|이전|이후|전후)[^.!?。]*[.!?。]?', re.IGNORECASE)
_INSIGHT_KEYWORDS = [
    '핵심', '중요', '결론', '요약', '포인트', '주목', '의미',
    '시사점', '교훈', '전략', '비결', '원칙',
]


def extract_snippets(content: str, max_count: int = 10) -> dict:
    """콘텐츠에서 소셜 공유용 스니펫을 추출합니다.

    Args:
        content: 분석할 콘텐츠
        max_count: 최대 추출 수 (기본 10)

    Returns:
        {
            "snippets": [
                {
                    "type": "statistic" | "quote" | "insight" | "comparison",
                    "text": str,
                    "char_count": int,
                    "social_ready": bool (280자 이하면 True),
                    "suggested_platform": str,
                }
            ],
            "total": int,
            "best_snippet": str | None,
        }
    """
    if not content or not content.strip():
        return {
            'snippets': [],
            'total': 0,
            'best_snippet': None,
        }

    plain = _strip_markdown(content)
    snippets = []
    seen_texts = set()

    # 1) 통계/숫자 스니펫
    for match in _STAT_PATTERN.finditer(plain):
        text = _clean_snippet(match.group())
        if text and text not in seen_texts and 20 <= len(text) <= 200:
            snippets.append(_make_snippet(text, 'statistic'))
            seen_texts.add(text)

    # 2) 인용문 스니펫
    for match in _QUOTE_PATTERN.finditer(plain):
        text = match.group(1).strip()
        if text and text not in seen_texts:
            snippets.append(_make_snippet(text, 'quote'))
            seen_texts.add(text)

    # 3) 비교/대비 스니펫
    for match in _COMPARISON_PATTERN.finditer(plain):
        text = _clean_snippet(match.group())
        if text and text not in seen_texts and 20 <= len(text) <= 200:
            snippets.append(_make_snippet(text, 'comparison'))
            seen_texts.add(text)

    # 4) 인사이트 키워드 기반
    sentences = re.split(r'[.!?。]\s*', plain)
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20 or sentence in seen_texts:
            continue
        if any(kw in sentence for kw in _INSIGHT_KEYWORDS):
            if len(sentence) <= 200:
                snippets.append(_make_snippet(sentence, 'insight'))
                seen_texts.add(sentence)

    # 중복 제거 후 제한
    snippets = snippets[:max_count]

    # 베스트 스니펫 선택 (통계 > 인용 > 인사이트 > 비교, 짧을수록 좋음)
    best = _select_best(snippets)

    return {
        'snippets': snippets,
        'total': len(snippets),
        'best_snippet': best,
    }


def _make_snippet(text: str, snippet_type: str) -> dict:
    """스니펫 객체 생성."""
    char_count = len(text)
    social_ready = char_count <= 280

    if char_count <= 140:
        platform = 'Twitter/X'
    elif char_count <= 280:
        platform = 'Twitter/X, Instagram'
    elif char_count <= 500:
        platform = 'LinkedIn, Threads'
    else:
        platform = 'Blog, Newsletter'

    return {
        'type': snippet_type,
        'text': text,
        'char_count': char_count,
        'social_ready': social_ready,
        'suggested_platform': platform,
    }


def _select_best(snippets: list) -> str | None:
    """최적 스니펫 선택."""
    if not snippets:
        return None

    priority = {'statistic': 0, 'quote': 1, 'insight': 2, 'comparison': 3}
    social_ready = [s for s in snippets if s['social_ready']]

    candidates = social_ready if social_ready else snippets
    candidates.sort(key=lambda s: (priority.get(s['type'], 9), s['char_count']))

    return candidates[0]['text'] if candidates else None


def _clean_snippet(text: str) -> str:
    """스니펫 텍스트 정리."""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    # 앞뒤 불완전한 문장 부호 제거
    text = re.sub(r'^[,;:\s]+', '', text)
    text = re.sub(r'[,;:\s]+$', '', text)
    return text


def _strip_markdown(text: str) -> str:
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
    return text
