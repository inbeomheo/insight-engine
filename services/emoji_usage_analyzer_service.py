"""
Emoji Usage Analyzer 서비스

콘텐츠에서 이모지 사용 패턴을 분석합니다.
이모지 빈도, 다양성, 위치(제목/본문), 과다 사용 여부를 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
from collections import Counter

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


def analyze_emoji_usage(content: str) -> dict:
    """이모지 사용 패턴을 분석합니다.

    Returns:
        emoji_list, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'emoji_list': [],
            'summary': {
                'total_emojis': 0,
                'unique_emojis': 0,
                'emoji_density': 0.0,
                'level': 'none',
                'in_headings': 0,
                'in_body': 0,
            },
            'score': 100.0,
            'suggestions': [],
        }

    all_emojis = _extract_emojis(content)
    total_emojis = len(all_emojis)

    if total_emojis == 0:
        word_count = len(content.split())
        return {
            'emoji_list': [],
            'summary': {
                'total_emojis': 0,
                'unique_emojis': 0,
                'emoji_density': 0.0,
                'level': 'none',
                'in_headings': 0,
                'in_body': 0,
            },
            'score': 100.0,
            'suggestions': ['이모지가 없습니다. 필요에 따라 적절히 사용하면 가독성을 높일 수 있습니다.'] if word_count > 50 else [],
        }

    # 단어 수
    word_count = len(content.split())
    density = round(total_emojis / max(word_count, 1) * 100, 1)

    # 고유 이모지
    emoji_counter = Counter(all_emojis)
    unique_emojis = len(emoji_counter)

    # 이모지 빈도 목록
    emoji_list = [
        {'emoji': emoji, 'count': count}
        for emoji, count in emoji_counter.most_common(20)
    ]

    # 제목 vs 본문 분류
    headings = _HEADING_RE.findall(content)
    heading_text = ' '.join(headings)
    heading_emojis = len(_extract_emojis(heading_text))

    # 본문에서 제목 제거
    body_text = _HEADING_RE.sub('', content)
    body_emojis = len(_extract_emojis(body_text))

    # 레벨 판정
    if density <= 1.0:
        level = 'minimal'
    elif density <= 3.0:
        level = 'moderate'
    elif density <= 5.0:
        level = 'heavy'
    else:
        level = 'excessive'

    # 점수 계산
    if density <= 2.0:
        score = 100.0
    elif density <= 4.0:
        score = 100.0 - (density - 2.0) * 10.0
    elif density <= 8.0:
        score = 80.0 - (density - 4.0) * 7.5
    else:
        score = max(0.0, 50.0 - (density - 8.0) * 5.0)

    # 다양성 보너스: 같은 이모지만 반복하면 감점
    if total_emojis >= 3 and unique_emojis == 1:
        score -= 10.0

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(density, level, total_emojis, unique_emojis, heading_emojis)

    return {
        'emoji_list': emoji_list,
        'summary': {
            'total_emojis': total_emojis,
            'unique_emojis': unique_emojis,
            'emoji_density': density,
            'level': level,
            'in_headings': heading_emojis,
            'in_body': body_emojis,
        },
        'score': score,
        'suggestions': suggestions,
    }


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
