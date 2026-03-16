"""
Emoji Usage Analyzer 서비스

콘텐츠에서 이모지 사용 패턴을 분석합니다.
이모지 빈도, 다양성, 위치(제목/본문), 과다 사용 여부를 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List
from collections import Counter
import logging

logger = logging.getLogger(__name__)

# 이모지 감지 패턴 (유니코드 범위 기반)
_EMOJI_RE = re.compile(
    '['
    '\U0001F600-\U0001F64F'  # 이모티콘
    '\U0001F300-\U0001F5FF'  # 기호 & 그림문자
    '\U0001F680-\U0001F6FF'  # 교통 & 지도
    '\U0001F1E0-\U0001F1FF'  # 국기
    '\U00002702-\U000027B0'  # Dingbats
    '\U0001F900-\U0001F9FF'  # 보충 이모지
    '\U0001FA00-\U0001FA6F'  # 체스 기호
    '\U0001FA70-\U0001FAFF'  # 기호 확장
    '\U00002600-\U000026FF'  # 기타 기호
    '\U00002049-\U00002B55'  # 기타 기호 (화살표 등)
    ']+', re.UNICODE
)

_HEADING_RE = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')


def _extract_emojis(text: str) -> List[str]:
    """텍스트에서 개별 이모지를 추출합니다."""
    matches = _EMOJI_RE.findall(text)
    # 각 매치를 개별 문자로 분리
    emojis = []
    for m in matches:
        for ch in m:
            if _EMOJI_RE.match(ch):
                emojis.append(ch)
    return emojis


_EMPTY_RESULT = {
    'emoji_list': [],
    'summary': {
        'total_emojis': 0, 'unique_emojis': 0, 'emoji_density': 0.0,
        'level': 'none', 'in_headings': 0, 'in_body': 0,
    },
    'score': 100.0,
    'suggestions': [],
}


def _analyze_distribution(content: str, all_emojis: List[str]) -> tuple:
    """이모지의 빈도, 위치(제목/본문)를 분석합니다.

    Returns:
        (emoji_list, density, unique_emojis, heading_emojis, body_emojis)
    """
    word_count = len(content.split())
    density = round(len(all_emojis) / max(word_count, 1) * 100, 1)

    emoji_counter = Counter(all_emojis)
    emoji_list = [
        {'emoji': emoji, 'count': count}
        for emoji, count in emoji_counter.most_common(20)
    ]

    headings = _HEADING_RE.findall(content)
    heading_emojis = len(_extract_emojis(' '.join(headings)))
    body_emojis = len(_extract_emojis(_HEADING_RE.sub('', content)))

    return emoji_list, density, len(emoji_counter), heading_emojis, body_emojis


def _compute_emoji_score(density: float, total: int, unique: int) -> tuple:
    """밀도 기반으로 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if density <= 1.0:
        level = 'minimal'
    elif density <= 3.0:
        level = 'moderate'
    elif density <= 5.0:
        level = 'heavy'
    else:
        level = 'excessive'

    if density <= 2.0:
        score = 100.0
    elif density <= 4.0:
        score = 100.0 - (density - 2.0) * 10.0
    elif density <= 8.0:
        score = 80.0 - (density - 4.0) * 7.5
    else:
        score = max(0.0, 50.0 - (density - 8.0) * 5.0)

    if total >= 3 and unique == 1:
        score -= 10.0

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_emoji_usage(content: str) -> dict:
    """이모지 사용 패턴을 분석합니다.

    Returns:
        emoji_list, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        all_emojis = _extract_emojis(content)
        if not all_emojis:
            word_count = len(content.split())
            suggestions = ['이모지가 없습니다. 필요에 따라 적절히 사용하면 가독성을 높일 수 있습니다.'] if word_count > 50 else []
            return {**_EMPTY_RESULT, 'suggestions': suggestions}

        emoji_list, density, unique_emojis, heading_emojis, body_emojis = (
            _analyze_distribution(content, all_emojis)
        )
        score, level = _compute_emoji_score(density, len(all_emojis), unique_emojis)
        suggestions = _generate_suggestions(density, level, len(all_emojis), unique_emojis, heading_emojis)

        return {
            'emoji_list': emoji_list,
            'summary': {
                'total_emojis': len(all_emojis), 'unique_emojis': unique_emojis,
                'emoji_density': density, 'level': level,
                'in_headings': heading_emojis, 'in_body': body_emojis,
            },
            'score': score,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}



def _generate_suggestions(density: float, level: str, total: int,
                           unique: int, in_headings: int) -> List[str]:
    suggestions = []
    level_labels = {
        'minimal': '최소', 'moderate': '적정',
        'heavy': '많음', 'excessive': '과다', 'none': '없음',
    }

    suggestions.append(
        f'이모지 밀도 {density}% ({level_labels.get(level, level)}). '
        f'총 {total}개, 고유 {unique}종.'
    )

    if level == 'excessive':
        suggestions.append(
            '이모지가 과도합니다. 핵심 포인트에만 사용하세요.'
        )
    elif level == 'heavy':
        suggestions.append(
            '이모지가 많은 편입니다. 섹션 제목이나 강조 포인트에만 제한하세요.'
        )

    if total >= 3 and unique == 1:
        suggestions.append(
            '같은 이모지만 반복됩니다. 다양한 이모지를 사용하면 더 효과적입니다.'
        )

    if in_headings == 0 and total > 0:
        suggestions.append(
            '제목에 이모지가 없습니다. 제목에 적절한 이모지를 추가하면 시선을 끌 수 있습니다.'
        )

    return suggestions
