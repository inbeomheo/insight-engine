"""
핵심 요약(Key Takeaways) 추출 서비스

콘텐츠에서 가장 중요한 포인트를 규칙 기반으로 추출합니다.
AI 호출 없이 문장 점수 기반으로 즉시 처리.
"""
import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# 중요도 부스트 키워드
_IMPORTANCE_KEYWORDS = [
    '핵심', '중요', '결론', '요약', '결국', '따라서', '즉',
    '첫째', '둘째', '셋째', '마지막으로', '정리하면',
    '반드시', '필수', '꼭', '주목', '기억',
    'key', 'important', 'conclusion', 'summary', 'must', 'essential',
]

# 감점 키워드 (부수적 내용)
_FILLER_KEYWORDS = [
    '그런데', '참고로', '여담으로', '아무튼', '어쨌든',
    '부연하면', '덧붙이면', '사족이지만',
]

# 마크다운 헤딩 패턴
_HEADING_PATTERN = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)
# 불릿/번호 리스트 패턴
_LIST_PATTERN = re.compile(r'^[\s]*[-*•]\s+|^[\s]*\d+[.)]\s+', re.MULTILINE)
# 볼드 텍스트 패턴
_BOLD_PATTERN = re.compile(r'\*\*(.+?)\*\*')
# 숫자/통계 패턴
_STAT_PATTERN = re.compile(r'\d+[%배만억천]|\d+\.\d+')


def _split_sentences(text: str) -> List[str]:
    """텍스트를 문장 단위로 분리합니다."""
    # 마크다운 헤딩 제거
    cleaned = _HEADING_PATTERN.sub('', text)
    # 문장 분리
    sentences = re.split(r'(?<=[.!?])\s+|\n+', cleaned)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def _score_sentence(sentence: str, position: float, total_sentences: int) -> float:
    """문장의 중요도 점수를 계산합니다.

    Args:
        sentence: 평가할 문장
        position: 문장의 상대 위치 (0.0 ~ 1.0)
        total_sentences: 전체 문장 수

    Returns:
        중요도 점수 (0.0 ~ 1.0)
    """
    score = 0.0

    # 1) 키워드 부스트 (최대 0.3)
    lower = sentence.lower()
    keyword_hits = sum(1 for kw in _IMPORTANCE_KEYWORDS if kw in lower)
    score += min(0.3, keyword_hits * 0.1)

    # 2) 필러 감점 (최대 -0.2)
    filler_hits = sum(1 for kw in _FILLER_KEYWORDS if kw in lower)
    score -= min(0.2, filler_hits * 0.1)

    # 3) 위치 보너스: 도입부(0~0.1)와 결론부(0.85~1.0)
    if position < 0.1:
        score += 0.15
    elif position > 0.85:
        score += 0.2

    # 4) 볼드 텍스트 포함 보너스
    if _BOLD_PATTERN.search(sentence):
        score += 0.15

    # 5) 숫자/통계 포함 보너스
    if _STAT_PATTERN.search(sentence):
        score += 0.1

    # 6) 리스트 아이템 보너스
    if _LIST_PATTERN.match(sentence):
        score += 0.05

    # 7) 적절한 길이 보너스 (30~120자)
    length = len(sentence)
    if 30 <= length <= 120:
        score += 0.1
    elif length > 200:
        score -= 0.05

    return round(max(0.0, min(1.0, score)), 4)


def extract_takeaways(content: str, count: int = 5) -> dict:
    """콘텐츠에서 핵심 요약 포인트를 추출합니다.

    Args:
        content: 분석할 콘텐츠 (마크다운/텍스트)
        count: 추출할 요약 수 (기본 5, 최대 10)

    Returns:
        {
            'takeaways': [{'text': str, 'score': float, 'position': str}],
            'total': int,
            'source_sentences': int,
            'headings': [str],
        }
    """
    if not content or not content.strip():
        return {'takeaways': [], 'total': 0, 'source_sentences': 0, 'headings': []}

    count = max(1, min(10, count))
    text = content.strip()

    # 헤딩 추출
    headings = _HEADING_PATTERN.findall(text)

    # 문장 분리 및 점수화
    sentences = _split_sentences(text)
    if not sentences:
        return {'takeaways': [], 'total': 0, 'source_sentences': 0, 'headings': headings}

    total = len(sentences)
    scored = []
    for i, sent in enumerate(sentences):
        position = i / max(1, total - 1)
        score = _score_sentence(sent, position, total)
        # 위치 라벨
        if position < 0.2:
            pos_label = 'intro'
        elif position > 0.8:
            pos_label = 'conclusion'
        else:
            pos_label = 'body'
        scored.append({
            'text': _clean_sentence(sent),
            'score': score,
            'position': pos_label,
        })

    # 점수 기준 정렬, 상위 N개 선택
    scored.sort(key=lambda x: x['score'], reverse=True)
    takeaways = scored[:count]

    # 원본 순서로 재정렬 (자연스러운 흐름)
    sentence_order = {sent: i for i, sent in enumerate(sentences)}
    takeaways.sort(key=lambda x: sentence_order.get(_find_original(x['text'], sentences), 0))

    return {
        'takeaways': takeaways,
        'total': len(takeaways),
        'source_sentences': total,
        'headings': headings,
    }


def _clean_sentence(sentence: str) -> str:
    """문장 앞뒤 마크다운 기호 정리."""
    cleaned = sentence.strip()
    # 불릿/번호 접두사 제거
    cleaned = re.sub(r'^[-*•]\s+', '', cleaned)
    cleaned = re.sub(r'^\d+[.)]\s+', '', cleaned)
    # 볼드 마크다운 제거 (텍스트만 남김)
    cleaned = _BOLD_PATTERN.sub(r'\1', cleaned)
    return cleaned.strip()


def _find_original(cleaned: str, sentences: List[str]) -> str:
    """정리된 문장에서 원본 문장을 찾습니다."""
    for sent in sentences:
        if cleaned in sent or cleaned in _clean_sentence(sent):
            return sent
    return cleaned
