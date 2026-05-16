"""
약어(Abbreviation) 용어집 서비스

콘텐츠에서 '풀네임(ABBR)' 패턴을 탐지해 자동으로 용어집을 만들고,
약어가 첫 등장 시점을 추적하여 '첫 사용 시 풀네임 표기' 가이드를
제공합니다.

예) "자연어 처리(NLP)는 ..." → {'NLP': '자연어 처리'}

규칙:
- ABBR은 2~8자 영대문자(또는 대문자+숫자) 시퀀스.
- 괄호 앞 텍스트에서 최대 6단어(또는 어절)까지 풀네임 후보로 간주.
- 선택적으로 사용자 제공 glossary(dict)를 추가·병합.
"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# '풀네임(ABBR)' 형태 (반각 괄호)
_PAREN_ABBR = re.compile(r'([^\s()]+(?:[\s\u00A0][^\s()]+){0,5})\s*\(([A-Z][A-Z0-9]{1,7})\)')
# 약어 자체(대소문자 섞인 약어는 제외, 대문자만)
_ABBR_ONLY = re.compile(r'(?<![A-Za-z])([A-Z][A-Z0-9]{1,7})(?![A-Za-z])')

_CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```|~~~[\s\S]*?~~~')


def extract_abbreviations(
    content: str,
    user_glossary: Optional[Dict[str, str]] = None,
    min_occurrences: int = 1,
) -> dict:
    """콘텐츠에서 약어 정의를 추출하고 용어집을 만듭니다.

    Args:
        content: 마크다운 또는 일반 텍스트.
        user_glossary: 사용자 제공 {약어: 풀네임} 사전. 자동 감지 결과와 병합.
        min_occurrences: 용어집에 포함하려면 최소 몇 번 등장해야 하는지.

    Returns:
        {
            'glossary': {ABBR: fullname},
            'occurrences': {ABBR: count},
            'first_position': {ABBR: int},  # 본문 내 첫 등장 위치(문자 오프셋)
            'undefined': [ABBR, ...],        # 등장하지만 정의 못 찾은 약어
        }
    """
    if not content:
        return {
            'glossary': dict(user_glossary or {}),
            'occurrences': {},
            'first_position': {},
            'undefined': [],
        }

    # 코드 블록 제외
    sanitized = _CODE_BLOCK_PATTERN.sub('', content)

    glossary: Dict[str, str] = dict(user_glossary or {})
    for match in _PAREN_ABBR.finditer(sanitized):
        fullname_candidate = match.group(1).strip()
        abbr = match.group(2).strip()
        if not _is_plausible_pair(fullname_candidate, abbr):
            continue
        # 사용자 제공 항목을 우선 유지, 미정의인 것만 추가
        glossary.setdefault(abbr, fullname_candidate)

    occurrences: Dict[str, int] = {}
    first_position: Dict[str, int] = {}
    for match in _ABBR_ONLY.finditer(sanitized):
        abbr = match.group(1)
        occurrences[abbr] = occurrences.get(abbr, 0) + 1
        first_position.setdefault(abbr, match.start())

    # min_occurrences 미만은 용어집에서 제거
    filtered_glossary = {
        abbr: full for abbr, full in glossary.items()
        if occurrences.get(abbr, 0) >= min_occurrences
    }

    undefined = sorted(
        abbr for abbr, _ in occurrences.items()
        if abbr not in filtered_glossary
    )

    return {
        'glossary': filtered_glossary,
        'occurrences': occurrences,
        'first_position': first_position,
        'undefined': undefined,
    }


def annotate_first_use(
    content: str,
    glossary: Dict[str, str],
    only_missing: bool = True,
) -> dict:
    """약어 첫 등장 위치에 '풀네임(ABBR)'이 없으면 주석을 제안합니다.

    실제 콘텐츠는 수정하지 않고, 어떤 위치에 어떤 치환을 하면 좋을지
    제안 목록만 반환합니다. (안전한 '리뷰 후 적용' 플로우)
    """
    if not content or not glossary:
        return {'suggestions': [], 'already_defined': []}

    sanitized = _CODE_BLOCK_PATTERN.sub(
        lambda m: ' ' * len(m.group(0)), content,
    )

    already_defined_positions: Dict[str, int] = {}
    for match in _PAREN_ABBR.finditer(sanitized):
        abbr = match.group(2).strip()
        already_defined_positions.setdefault(abbr, match.start())

    suggestions: List[dict] = []
    already_defined: List[str] = []

    for abbr, fullname in glossary.items():
        if not abbr:
            continue
        # 이미 '풀네임(ABBR)'이 본문에 존재 → 스킵
        if abbr in already_defined_positions and only_missing:
            already_defined.append(abbr)
            continue

        # 첫 등장 위치 찾기
        first = None
        for match in _ABBR_ONLY.finditer(sanitized):
            if match.group(1) == abbr:
                first = match.start()
                break
        if first is None:
            continue

        suggestions.append({
            'abbr': abbr,
            'fullname': fullname,
            'position': first,
            'suggestion': f'{fullname}({abbr})',
            'context': _snippet(content, first),
        })

    return {'suggestions': suggestions, 'already_defined': sorted(already_defined)}


def format_glossary_markdown(
    glossary: Dict[str, str], title: str = '용어집',
) -> str:
    """용어집을 마크다운 정의 리스트 형식으로 포맷합니다."""
    if not glossary:
        return ''

    lines = [f'## {title}', '']
    for abbr in sorted(glossary.keys()):
        fullname = glossary[abbr]
        lines.append(f'- **{abbr}**: {fullname}')
    return '\n'.join(lines)


def _is_plausible_pair(fullname: str, abbr: str) -> bool:
    """풀네임과 약어가 그럴듯한 쌍인지 판단.

    규칙:
    - 풀네임이 빈 문자열이거나 3자 미만이면 거짓
    - 풀네임이 '영문 2개 이상 단어'로 구성되어 있으면 각 단어의 첫 글자 이니셜이
      약어 전체를 포함해야 함 (한 글자씩 같은 순서로 부분열이어야 함)
    - 비영문(한국어/일본어/중국어 등) 풀네임은 완전 매칭을 요구하지 않음
    """
    if not fullname or len(fullname) < 3:
        return False
    if not abbr:
        return False

    english_words = re.findall(r"[A-Za-z][A-Za-z'\-]*", fullname)
    # 영문 단어가 2개 이상이면 이니셜 부분열 매칭 요구
    if len(english_words) >= 2:
        initials = ''.join(w[0].upper() for w in english_words)
        if not _is_subsequence(abbr.upper(), initials):
            return False
    return True


def _is_subsequence(needle: str, haystack: str) -> bool:
    """`needle`의 글자가 `haystack`에서 동일 순서로 등장하는지 검사."""
    if not needle:
        return True
    it = iter(haystack)
    return all(ch in it for ch in needle)


def _snippet(text: str, position: int, window: int = 40) -> str:
    start = max(0, position - window)
    end = min(len(text), position + window)
    snippet = text[start:end].replace('\n', ' ').strip()
    prefix = '...' if start > 0 else ''
    suffix = '...' if end < len(text) else ''
    return f'{prefix}{snippet}{suffix}'
