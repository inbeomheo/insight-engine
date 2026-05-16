"""
콘텐츠 메타데이터 추출 서비스

콘텐츠에서 구조화된 메타데이터를 자동 추출합니다.
제목, 카테고리, 태그, 날짜, 언어, 콘텐츠 유형 등.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)
_DATE_PATTERN = re.compile(r'(\d{4})[-./ ](\d{1,2})[-./ ](\d{1,2})')
_KO_CHAR = re.compile(r'[가-힣]')
_EN_WORD = re.compile(r'[a-zA-Z]{3,}')
_CODE_BLOCK = re.compile(r'```')
_IMAGE = re.compile(r'!\[.*?\]\(.*?\)')
_LIST_ITEM = re.compile(r'^\s*[-*•]\s+|^\s*\d+[.)]\s+', re.MULTILINE)
_WORD = re.compile(r'[\w가-힣]+')

# 카테고리 키워드 매핑
_CATEGORY_KEYWORDS = {
    'technology': ['AI', '인공지능', '머신러닝', '프로그래밍', '코딩', '개발', '소프트웨어', 'API', '클라우드', '데이터'],
    'business': ['마케팅', '비즈니스', '수익', '매출', '전략', '투자', '스타트업', '경영', '성장'],
    'education': ['학습', '교육', '강의', '튜토리얼', '가이드', '입문', '기초', '실습'],
    'lifestyle': ['건강', '여행', '요리', '취미', '일상', '운동', '식단'],
    'creative': ['디자인', '창작', '글쓰기', '예술', '사진', '영상', '콘텐츠'],
    'science': ['연구', '논문', '실험', '과학', '물리', '화학', '생물'],
}

# 콘텐츠 유형 감지
_CONTENT_TYPE_SIGNALS = {
    'tutorial': ['방법', '하는 법', '따라하기', 'how to', 'step', '단계'],
    'review': ['리뷰', '후기', '비교', '평가', '장단점', 'review'],
    'news': ['발표', '출시', '업데이트', '소식', '뉴스'],
    'opinion': ['생각', '의견', '주장', '관점', '개인적'],
    'listicle': ['가지', '선정', 'top', 'best', '추천', '모음'],
    'guide': ['가이드', '완벽', '총정리', '핵심', '정리'],
}


def extract_metadata(content: str) -> dict:
    """콘텐츠에서 메타데이터를 추출합니다.

    Returns:
        {
            'title': str,
            'category': str,
            'content_type': str,
            'language': str,
            'tags': [str],
            'dates': [str],
            'word_count': int,
            'has_code': bool,
            'has_images': bool,
            'has_lists': bool,
            'estimated_reading_level': str,
        }
    """
    if not content or not content.strip():
        return _empty_result()

    text = content.strip()

    # 제목 추출 (첫 번째 H1 또는 가장 높은 레벨 헤딩)
    title = _extract_title(text)

    # 언어 감지
    language = _detect_language(text)

    # 카테고리 추론
    category = _infer_category(text)

    # 콘텐츠 유형 추론
    content_type = _infer_content_type(text)

    # 날짜 추출
    dates = [f'{m[0]}-{m[1].zfill(2)}-{m[2].zfill(2)}' for m in _DATE_PATTERN.findall(text)]

    # 자동 태그 (상위 빈도 키워드)
    tags = _extract_tags(text)

    # 요소 감지
    word_count = len(_WORD.findall(text))
    has_code = bool(_CODE_BLOCK.search(text))
    has_images = bool(_IMAGE.search(text))
    has_lists = bool(_LIST_ITEM.search(text))

    # 읽기 수준 추정
    reading_level = _estimate_reading_level(text, word_count)

    return {
        'title': title,
        'category': category,
        'content_type': content_type,
        'language': language,
        'tags': tags,
        'dates': list(set(dates))[:5],
        'word_count': word_count,
        'has_code': has_code,
        'has_images': has_images,
        'has_lists': has_lists,
        'estimated_reading_level': reading_level,
    }


def _extract_title(text: str) -> str:
    """첫 번째 헤딩을 제목으로 추출합니다."""
    match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # H1이 없으면 가장 높은 레벨
    headings = _HEADING_PATTERN.findall(text)
    return headings[0].strip() if headings else ''


def _detect_language(text: str) -> str:
    """주요 언어를 감지합니다."""
    ko = len(_KO_CHAR.findall(text))
    en = len(_EN_WORD.findall(text))
    if ko == 0 and en == 0:
        return 'unknown'
    if ko > en:
        return 'ko'
    if en > ko * 3:
        return 'en'
    return 'ko'  # 한국어 우선


def _infer_category(text: str) -> str:
    """키워드 기반 카테고리 추론."""
    lower = text.lower()
    scores = {}
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw.lower() in lower)

    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return 'general'
    return max(scores, key=scores.get)


def _infer_content_type(text: str) -> str:
    """콘텐츠 유형 추론."""
    lower = text.lower()
    scores = {}
    for ctype, signals in _CONTENT_TYPE_SIGNALS.items():
        scores[ctype] = sum(1 for s in signals if s.lower() in lower)

    max_score = max(scores.values()) if scores else 0
    if max_score == 0:
        return 'article'
    return max(scores, key=scores.get)


def _extract_tags(text: str, max_tags: int = 5) -> List[str]:
    """상위 빈도 키워드를 태그로 추출합니다."""
    stopwords = frozenset(['이', '그', '저', '것', '수', '등', '및', '또는', '위한', '대한',
                           '통해', '따라', '하는', '있는', '되는', '그리고', '하지만'])
    words = _WORD.findall(text)
    freq = {}
    for w in words:
        w_lower = w.lower()
        if len(w) >= 2 and w_lower not in stopwords:
            freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:max_tags]]


def _estimate_reading_level(text: str, word_count: int) -> str:
    """읽기 수준을 추정합니다."""
    sentences = re.split(r'[.!?。]+', text)
    sentence_count = max(1, len([s for s in sentences if s.strip()]))
    avg_words_per_sentence = word_count / sentence_count

    has_code = bool(_CODE_BLOCK.search(text))

    if has_code or avg_words_per_sentence > 25:
        return 'advanced'
    elif avg_words_per_sentence > 15:
        return 'intermediate'
    return 'beginner'


def _empty_result() -> dict:
    return {
        'title': '', 'category': 'general', 'content_type': 'article',
        'language': 'unknown', 'tags': [], 'dates': [],
        'word_count': 0, 'has_code': False, 'has_images': False,
        'has_lists': False, 'estimated_reading_level': 'beginner',
    }
