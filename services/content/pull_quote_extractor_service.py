"""
Pull Quote(강조 인용구) 추출 서비스

긴 콘텐츠에서 '블록 인용구로 강조할 만한' 문장을 자동으로 추출합니다.
에디토리얼 레이아웃, 소셜 카드, 하이라이트 배너에 사용됩니다.

점수 구성 요소:
- 길이 점수: 40~140자 범위일 때 최고점 (짧은 한 줄 문장을 선호)
- 키워드 점수: 독자의 시선을 끄는 단어(핵심/비결/이유 등) 포함 여부
- 구두점 점수: 마침표/느낌표/물음표 종결 완결성
- 위치 점수: 서두/말미 문장은 가산점 (요약적 역할)
"""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# 인상적인 문장에 자주 나타나는 키워드 (한국어)
_IMPACT_KEYWORDS_KO = {
    '핵심', '비결', '이유', '중요한', '본질', '결론', '반드시',
    '필수', '사실', '진짜', '실제로', '놀랍게도', '결정적',
}
# 영어 임팩트 키워드
_IMPACT_KEYWORDS_EN = {
    'essential', 'critical', 'key', 'secret', 'truth', 'reason',
    'must', 'never', 'always', 'remember', 'important',
}

# 이상적인 pull quote 길이 (글자수 기준)
IDEAL_MIN_LENGTH = 40
IDEAL_MAX_LENGTH = 140
HARD_MIN_LENGTH = 20
HARD_MAX_LENGTH = 250

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?。！？])\s+|(?<=[다요죠네])\.\s+')
_CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```|~~~[\s\S]*?~~~')
_HEADING_LINE_PATTERN = re.compile(r'^#{1,6}\s+.*$', re.MULTILINE)
_IMAGE_PATTERN = re.compile(r'!\[[^\]]*\]\([^)]+\)')
_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_BOLD_ITALIC_PATTERN = re.compile(r'[*_]{1,3}([^*_]+)[*_]{1,3}')
_LIST_PREFIX = re.compile(r'^\s*([-*•]|\d+[.)])\s+')


def extract_pull_quotes(
    content: str,
    top_n: int = 5,
    language: str = 'ko',
    min_length: int = HARD_MIN_LENGTH,
    max_length: int = HARD_MAX_LENGTH,
) -> dict:
    """콘텐츠에서 pull quote 후보 문장을 점수 순으로 추출합니다.

    Args:
        content: 마크다운 또는 일반 텍스트.
        top_n: 반환할 상위 인용구 개수. 기본 5.
        language: 'ko' 또는 'en'. 키워드 사전을 결정.
        min_length: 후보에 포함할 최소 글자수.
        max_length: 후보에 포함할 최대 글자수.

    Returns:
        {
            'quotes': [{'text': str, 'score': float, 'length': int, 'position': int}],
            'total_candidates': int,
            'source_sentence_count': int,
        }
    """
    if not content or not content.strip():
        return {'quotes': [], 'total_candidates': 0, 'source_sentence_count': 0}

    if min_length < 1:
        min_length = 1
    if max_length <= min_length:
        max_length = min_length + 1

    sentences = _extract_sentences(content)
    source_count = len(sentences)

    candidates = []
    for idx, sentence in enumerate(sentences):
        text = sentence.strip()
        length = len(text)
        if length < min_length or length > max_length:
            continue

        score = _score_sentence(
            text, position=idx, total=source_count, language=language,
        )
        candidates.append({
            'text': text,
            'score': round(score, 2),
            'length': length,
            'position': idx,
        })

    candidates.sort(key=lambda c: c['score'], reverse=True)
    return {
        'quotes': candidates[:top_n] if top_n > 0 else candidates,
        'total_candidates': len(candidates),
        'source_sentence_count': source_count,
    }


def _extract_sentences(content: str) -> List[str]:
    """마크다운을 정제한 뒤 문장 단위로 분리합니다."""
    text = _CODE_BLOCK_PATTERN.sub(' ', content)
    text = _HEADING_LINE_PATTERN.sub(' ', text)
    text = _IMAGE_PATTERN.sub(' ', text)
    text = _LINK_PATTERN.sub(r'\1', text)
    text = _BOLD_ITALIC_PATTERN.sub(r'\1', text)

    # 리스트 프리픽스 제거 (라인 단위)
    cleaned_lines = []
    for line in text.split('\n'):
        cleaned = _LIST_PREFIX.sub('', line)
        cleaned_lines.append(cleaned)
    text = '\n'.join(cleaned_lines)

    # 문장 분리
    sentences = _SENTENCE_SPLIT.split(text)
    result = []
    for s in sentences:
        s = ' '.join(s.split())  # 공백 정규화
        if s:
            result.append(s)
    return result


def _score_sentence(
    sentence: str, position: int, total: int, language: str,
) -> float:
    """문장 점수 0~100 스케일."""
    length = len(sentence)

    # 1) 길이 점수 (최대 40점)
    if IDEAL_MIN_LENGTH <= length <= IDEAL_MAX_LENGTH:
        length_score = 40.0
    elif length < IDEAL_MIN_LENGTH:
        length_score = 40.0 * length / IDEAL_MIN_LENGTH
    else:  # length > IDEAL_MAX_LENGTH
        overflow = length - IDEAL_MAX_LENGTH
        penalty = min(40.0, overflow / 5)
        length_score = max(0.0, 40.0 - penalty)

    # 2) 키워드 점수 (최대 30점)
    if language == 'en':
        lower = sentence.lower()
        # 영어는 단어 경계(`\b`) 매칭으로 부분 문자열 오탐 방지 ('key' in 'monkey')
        hits = sum(
            1 for kw in _IMPACT_KEYWORDS_EN
            if re.search(rf'\b{re.escape(kw.lower())}\b', lower)
        )
    else:
        # 한국어는 형태소 경계가 없어 단순 substring 매칭 유지
        hits = sum(1 for kw in _IMPACT_KEYWORDS_KO if kw in sentence)
    keyword_score = min(30.0, hits * 10.0)

    # 3) 구두점 점수 (최대 10점)
    if sentence.endswith(('.', '!', '?', '다.', '요.', '네.', '죠.')):
        punct_score = 10.0
    elif sentence.endswith((',', ';')):
        punct_score = 2.0
    else:
        punct_score = 5.0

    # 4) 위치 점수 (최대 20점)
    if total <= 1:
        position_score = 20.0
    else:
        normalized = position / max(1, total - 1)
        # 서두/말미 가산: U자 형태
        if normalized < 0.15 or normalized > 0.85:
            position_score = 20.0
        elif normalized < 0.3 or normalized > 0.7:
            position_score = 12.0
        else:
            position_score = 6.0

    return length_score + keyword_score + punct_score + position_score


def format_as_blockquote(quote_text: str, attribution: Optional[str] = None) -> str:
    """선택한 인용구를 마크다운 블록쿼트로 변환합니다."""
    if not quote_text or not quote_text.strip():
        return ''
    lines = ['> ' + line for line in quote_text.strip().split('\n')]
    block = '\n'.join(lines)
    if attribution:
        block += f'\n> \n> — {attribution}'
    return block
