"""
해시태그 자동 생성 서비스

콘텐츠에서 핵심 키워드를 추출하여 해시태그를 생성합니다.
TF 기반 키워드 추출 + 불용어 필터링으로 AI 호출 없이 처리.
"""
import logging
import re
from collections import Counter
from typing import List

logger = logging.getLogger(__name__)

# 한국어 불용어 (해시태그로 부적합)
_STOPWORDS_KO = frozenset([
    '이', '그', '저', '것', '수', '등', '및', '또는', '하는', '있는',
    '되는', '위한', '대한', '통해', '따라', '보다', '때문', '이후',
    '경우', '바로', '사실', '정도', '부분', '중요', '다양', '필요',
    '위해', '함께', '최근', '현재', '가장', '매우', '이미',
    '그리고', '하지만', '그러나', '따라서', '그래서', '또한',
])

# 영어 불용어
_STOPWORDS_EN = frozenset([
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
    'would', 'could', 'should', 'may', 'might', 'can', 'shall',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
    'as', 'into', 'through', 'during', 'before', 'after', 'and',
    'but', 'or', 'not', 'no', 'this', 'that', 'these', 'those',
    'it', 'its', 'they', 'them', 'their', 'we', 'our', 'you',
    'your', 'he', 'she', 'his', 'her', 'my', 'me', 'so', 'if',
    'than', 'too', 'very', 'just', 'about', 'up', 'out', 'all',
])

_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)
_WORD_PATTERN = re.compile(r'[가-힣]{2,}|[a-zA-Z]{3,}')
_BOLD_PATTERN = re.compile(r'\*\*(.+?)\*\*')


def _extract_words(text: str) -> List[str]:
    """텍스트에서 단어를 추출합니다."""
    return _WORD_PATTERN.findall(text)


def _is_stopword(word: str) -> bool:
    """불용어인지 확인합니다."""
    lower = word.lower()
    return lower in _STOPWORDS_KO or lower in _STOPWORDS_EN


def _format_hashtag(word: str) -> str:
    """단어를 해시태그 형식으로 변환합니다."""
    # 한국어: 그대로, 영어: PascalCase 유지
    cleaned = re.sub(r'[^가-힣a-zA-Z0-9]', '', word)
    if not cleaned:
        return ''
    return f'#{cleaned}'


def generate_hashtags(content: str, count: int = 10,
                      include_headings: bool = True) -> dict:
    """콘텐츠에서 해시태그를 생성합니다.

    Args:
        content: 분석할 콘텐츠
        count: 생성할 해시태그 수 (기본 10, 최대 30)
        include_headings: 헤딩에서도 키워드 추출 여부

    Returns:
        {
            'hashtags': [{'tag': str, 'score': float}],
            'total': int,
            'top_keywords': [str],
            'category_tags': [str],
        }
    """
    if not content or not content.strip():
        return {'hashtags': [], 'total': 0, 'top_keywords': [], 'category_tags': []}

    count = max(1, min(30, count))
    text = content.strip()

    # 키워드 점수 계산
    word_scores = Counter()

    # 1) 본문 단어 빈도
    words = _extract_words(text)
    for word in words:
        if not _is_stopword(word) and len(word) >= 2:
            word_scores[word] += 1

    # 2) 헤딩 단어 가중치 (x3)
    if include_headings:
        headings = _HEADING_PATTERN.findall(text)
        for heading in headings:
            heading_words = _extract_words(heading)
            for word in heading_words:
                if not _is_stopword(word):
                    word_scores[word] += 3

    # 3) 볼드 단어 가중치 (x2)
    bold_matches = _BOLD_PATTERN.findall(text)
    for bold_text in bold_matches:
        bold_words = _extract_words(bold_text)
        for word in bold_words:
            if not _is_stopword(word):
                word_scores[word] += 2

    if not word_scores:
        return {'hashtags': [], 'total': 0, 'top_keywords': [], 'category_tags': []}

    # 상위 키워드 선택
    max_score = max(word_scores.values())
    top_words = word_scores.most_common(count)

    hashtags = []
    for word, score in top_words:
        tag = _format_hashtag(word)
        if tag:
            hashtags.append({
                'tag': tag,
                'score': round(score / max_score, 2),
            })

    # 카테고리 태그 (상위 3개 2글자+ 한국어 키워드)
    category_tags = []
    for word, _ in top_words[:5]:
        if re.match(r'^[가-힣]+$', word) and len(word) >= 2:
            category_tags.append(f'#{word}')
        if len(category_tags) >= 3:
            break

    return {
        'hashtags': hashtags,
        'total': len(hashtags),
        'top_keywords': [w for w, _ in top_words[:5]],
        'category_tags': category_tags,
    }
