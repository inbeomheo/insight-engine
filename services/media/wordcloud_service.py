"""
워드클라우드 서비스

텍스트에서 단어 빈도를 계산하여 SVG 태그 클라우드를 생성합니다.
외부 패키지 없이 순수 Python으로 구현합니다.
"""
import logging
import math
import re
from collections import Counter
from html import escape

logger = logging.getLogger(__name__)

# 한국어/영어 불용어
_STOPWORDS = {
    # 한국어
    '이', '그', '저', '것', '수', '등', '때', '중', '더', '를', '을', '에', '의', '가',
    '은', '는', '로', '으로', '에서', '와', '과', '도', '또', '및', '한', '된', '되',
    '하는', '있는', '하고', '이런', '그런', '이것', '그것', '있다', '없다', '한다',
    '합니다', '했습니다', '있습니다', '없습니다', '대한', '위한', '통해', '위해',
    # 영어
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
    'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
    'this', 'that', 'these', 'those', 'it', 'its', 'he', 'she', 'they',
    'them', 'we', 'you', 'i', 'me', 'my', 'your', 'his', 'her', 'our',
}

# SVG 색상 팔레트
_COLORS = [
    '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981',
    '#06b6d4', '#6366f1', '#f43f5e', '#84cc16', '#14b8a6',
]


def generate_wordcloud(text: str, max_words: int = 60, width: int = 800, height: int = 400) -> str:
    """텍스트에서 워드클라우드 SVG를 생성합니다.

    Args:
        text: 분석할 텍스트
        max_words: 최대 표시 단어 수
        width: SVG 너비
        height: SVG 높이

    Returns:
        SVG 문자열
    """
    if not text or not text.strip():
        raise ValueError('분석할 텍스트가 없습니다.')

    try:
        word_counts = _count_words(text, max_words)
        if not word_counts:
            raise ValueError('추출된 단어가 없습니다.')

        return _render_svg(word_counts, width, height)
    except ValueError:
        raise
    except Exception as e:
        logger.error('워드클라우드 생성 중 오류: %s', e)
        raise RuntimeError(f'워드클라우드 생성 실패: {e}') from e


def _count_words(text: str, max_words: int) -> list[tuple[str, int]]:
    """텍스트에서 단어 빈도를 계산합니다."""
    # 마크다운/HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'[#*_`~\[\](){}|>]', '', text)
    text = re.sub(r'https?://\S+', '', text)

    # 단어 추출 (한국어 2자 이상, 영어 3자 이상)
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', text.lower())

    # 불용어 제거
    words = [w for w in words if w not in _STOPWORDS]

    return Counter(words).most_common(max_words)


def _render_svg(word_counts: list[tuple[str, int]], width: int, height: int) -> str:
    """단어 빈도 목록을 SVG로 렌더링합니다."""
    max_count = word_counts[0][1] if word_counts else 1
    min_size = 12
    max_size = 48

    elements = []
    for idx, (word, count) in enumerate(word_counts):
        # 빈도에 비례한 글자 크기
        ratio = count / max_count
        font_size = min_size + (max_size - min_size) * ratio

        # 나선형 배치
        angle = idx * 2.4  # 황금각
        radius = 15 * math.sqrt(idx + 1)
        x = width / 2 + radius * math.cos(angle)
        y = height / 2 + radius * math.sin(angle)

        # 경계 내로 클리핑
        x = max(font_size, min(width - font_size * len(word) * 0.5, x))
        y = max(font_size, min(height - font_size, y))

        color = _COLORS[idx % len(_COLORS)]
        opacity = 0.7 + 0.3 * ratio

        elements.append(
            f'  <text x="{x:.1f}" y="{y:.1f}" '
            f'font-size="{font_size:.1f}" fill="{color}" opacity="{opacity:.2f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-family="Pretendard, sans-serif" font-weight="{500 + int(ratio * 400)}">'
            f'{escape(word)}</text>'
        )

    svg_elements = '\n'.join(elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" width="{width}" height="{height}">\n'
        f'  <rect width="100%" height="100%" fill="transparent"/>\n'
        f'{svg_elements}\n'
        f'</svg>'
    )
