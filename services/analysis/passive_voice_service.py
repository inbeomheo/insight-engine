"""
피동 표현 감지 서비스

한국어 콘텐츠에서 피동 표현을 감지하고
능동문으로의 전환을 제안합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 한국어 피동 접미사 패턴
_PASSIVE_SUFFIXES = [
    # -이/히/리/기 피동
    r'[가-힣]+이다(?:\.|\s|$)',
    r'[가-힣]+[되](?:었|는|ㄴ|다|고|어|지|면)',
    # -되다 피동 (가장 흔함)
    r'[가-힣]+되(?:었|는|다|고|어|지|면|었다|는다|ㄴ다)',
    # -아/어지다 피동
    r'[가-힣]+(?:아|어)지(?:고|는|다|면|ㄴ|었)',
    # -받다 피동
    r'[가-힣]+받(?:는|다|고|았|은|을)',
    # -당하다 피동
    r'[가-힣]+당하(?:는|다|고|였|ㅆ)',
]

# 피동 키워드 (직접 매칭)
_PASSIVE_KEYWORDS = [
    '되었다', '되었습니다', '되어', '되는', '된다', '됩니다', '되고',
    '받았다', '받았습니다', '받는', '받게',
    '당했다', '당하고', '당하는',
    '여겨진다', '알려져', '알려진', '알려졌',
    '불리는', '불린다', '불려진',
    '만들어진', '만들어졌', '이루어진', '이루어졌',
    '쓰여진', '쓰여졌', '사용되', '활용되',
    '발견되', '확인되', '진행되', '완료되', '수행되',
    '제공되', '작성되', '구성되', '설계되', '개발되',
    '처리되', '생성되', '저장되', '전달되', '변환되',
]

# 능동 전환 제안 매핑
_PASSIVE_TO_ACTIVE = {
    '사용되': '사용하',
    '활용되': '활용하',
    '발견되': '발견하',
    '확인되': '확인하',
    '진행되': '진행하',
    '완료되': '완료하',
    '수행되': '수행하',
    '제공되': '제공하',
    '작성되': '작성하',
    '구성되': '구성하',
    '설계되': '설계하',
    '개발되': '개발하',
    '처리되': '처리하',
    '생성되': '생성하',
    '저장되': '저장하',
    '전달되': '전달하',
    '변환되': '변환하',
    '알려져': '알려',
    '만들어진': '만든',
    '이루어진': '이룬',
}


_EMPTY_RESULT = {
    'passive_expressions': [],
    'summary': {'total': 0, 'sentence_count': 0, 'passive_ratio': 0},
    'score': 100,
    'suggestions': [],
}


def _scan_passive_expressions(sentences: list) -> tuple:
    """문장 목록에서 피동 표현을 스캔합니다.

    Returns:
        (passives, passive_sentence_count)
    """
    passives = []
    passive_sentence_count = 0

    for sent in sentences:
        found_in_sentence = False
        for kw in _PASSIVE_KEYWORDS:
            if kw in sent:
                passives.append({
                    'text': kw,
                    'sentence': sent[:80] + '...' if len(sent) > 80 else sent,
                    'suggestion': _suggest_active(kw, sent),
                })
                found_in_sentence = True
                break

        if found_in_sentence:
            passive_sentence_count += 1

    return passives, passive_sentence_count


def detect_passive(content: str) -> dict:
    """콘텐츠에서 피동 표현을 감지합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        passive_expressions, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        sentences = [s.strip() for s in re.split(r'[.!?。]\s*|\n+', content)
                     if len(s.strip()) >= 5]
        if not sentences:
            return {**_EMPTY_RESULT, 'suggestions': ['분석할 문장이 없습니다.']}

        passives, passive_sentence_count = _scan_passive_expressions(sentences)
        total_sentences = len(sentences)
        passive_ratio = round(passive_sentence_count / total_sentences * 100, 1)

        return {
            'passive_expressions': passives,
            'summary': {
                'total': len(passives),
                'sentence_count': total_sentences,
                'passive_ratio': passive_ratio,
            },
            'score': max(0, min(100, 100 - int(passive_ratio * 1.5))),
            'suggestions': _generate_suggestions(passive_ratio, len(passives), total_sentences),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _suggest_active(keyword: str, sentence: str) -> str:
    """피동 표현에 대한 능동 전환을 제안합니다."""
    for passive, active in _PASSIVE_TO_ACTIVE.items():
        if passive in keyword or keyword.startswith(passive):
            return f'"{passive}" → "{active}"로 능동 전환을 고려하세요.'
    return '주어를 명시하고 능동형으로 바꿔 보세요.'


def _generate_suggestions(ratio: float, count: int, total: int) -> list:
    suggestions = []

    if count == 0:
        suggestions.append('피동 표현이 없습니다. 명확하고 능동적인 글입니다.')
        return suggestions

    if ratio > 40:
        suggestions.append(f'피동 표현 비율({ratio}%)이 높습니다. 주어를 명시하고 능동문으로 바꾸면 가독성이 크게 향상됩니다.')
    elif ratio > 20:
        suggestions.append(f'피동 표현({count}개)이 다소 많습니다. 핵심 문장은 능동형으로 바꿔 보세요.')
    else:
        suggestions.append(f'피동 표현이 {count}개로 적절한 수준입니다.')

    if count > 0:
        suggestions.append('피동 표현은 객관성이 필요한 곳(학술, 보고서)에서는 자연스럽지만, 블로그나 마케팅에서는 능동형이 효과적입니다.')

    return suggestions
