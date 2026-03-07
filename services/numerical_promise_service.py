"""
수치 약속 이행 검증 서비스 (Numerical Promise Integrity Checker)

제목/소제목에서 "7가지", "3단계", "5분" 등 수치 약속을 감지하고
본문에서 실제로 이행되는지 검사합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 수치 약속 감지 패턴 (그룹1: 숫자, 그룹2: 단위)
_PROMISE_PATTERNS = [
    # "N가지" — 5가지 방법, 10가지 팁
    re.compile(r'(\d+)\s*가지'),
    # "N단계" — 3단계 가이드
    re.compile(r'(\d+)\s*단계'),
    # "N분" — 5분 요약, 10분 완성
    re.compile(r'(\d+)\s*분'),
    # "TopN" / "TOP N" — Top 10, TOP5
    re.compile(r'[Tt][Oo][Pp]\s*(\d+)'),
    # "N선" — 베스트 5선, 추천 10선
    re.compile(r'(\d+)\s*선'),
    # "N개" — 3개 비법, 7개 포인트
    re.compile(r'(\d+)\s*개'),
    # "N steps" — 영문 패턴
    re.compile(r'(\d+)\s*steps?', re.IGNORECASE),
    # "N tips" — 영문 패턴
    re.compile(r'(\d+)\s*tips?', re.IGNORECASE),
]

# 제목/소제목 추출 패턴 (마크다운 헤딩)
_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 번호 매기기 패턴들
_NUMBERED_LIST_PATTERNS = [
    # "1. ", "2. ", "10. " (마크다운 순서 목록)
    re.compile(r'^\s*(\d+)\.\s+', re.MULTILINE),
    # "1) ", "2) " 형식
    re.compile(r'^\s*(\d+)\)\s+', re.MULTILINE),
    # "(1)", "(2)" 형식
    re.compile(r'^\s*\((\d+)\)\s*', re.MULTILINE),
]

# 한국어 서수 매핑 (최대 20까지)
_KOREAN_ORDINALS = {
    '첫째': 1, '둘째': 2, '셋째': 3, '넷째': 4, '다섯째': 5,
    '여섯째': 6, '일곱째': 7, '여덟째': 8, '아홉째': 9, '열째': 10,
    '첫번째': 1, '두번째': 2, '세번째': 3, '네번째': 4, '다섯번째': 5,
    '여섯번째': 6, '일곱번째': 7, '여덟번째': 8, '아홉번째': 9, '열번째': 10,
    '첫 번째': 1, '두 번째': 2, '세 번째': 3, '네 번째': 4, '다섯 번째': 5,
}

_KOREAN_ORDINAL_PATTERN = re.compile(
    '|'.join(re.escape(k) for k in sorted(_KOREAN_ORDINALS.keys(), key=len, reverse=True))
)


def check_numerical_promises(content: str) -> dict:
    """콘텐츠의 수치 약속 이행 여부를 검증합니다.

    Args:
        content: 검사할 마크다운 콘텐츠

    Returns:
        {
            "promises": [{"text": str, "promised_number": int,
                          "actual_count": int, "status": str, "location": str}],
            "integrity_score": float,  # 0-100
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'promises': [],
            'integrity_score': 100.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 1. 제목/소제목에서 수치 약속 감지
    promises = _detect_promises(content)

    if not promises:
        return {
            'promises': [],
            'integrity_score': 100.0,
            'suggestions': ['수치 약속이 감지되지 않았습니다.'],
        }

    # 2. 각 약속에 대해 이행 여부 검증
    for promise in promises:
        actual = _count_fulfillment(content, promise)
        promise['actual_count'] = actual
        promise['status'] = _determine_status(promise['promised_number'], actual)

    # 3. 무결성 점수 계산
    integrity_score = _calculate_integrity_score(promises)

    # 4. 개선 제안 생성
    suggestions = _generate_suggestions(promises)

    return {
        'promises': promises,
        'integrity_score': integrity_score,
        'suggestions': suggestions,
    }


def _detect_promises(content: str) -> list:
    """제목/소제목과 본문 첫 줄에서 수치 약속을 감지합니다."""
    promises = []
    seen = set()  # 중복 방지 (위치, 숫자)

    # 마크다운 헤딩에서 약속 찾기
    headings = _HEADING_PATTERN.findall(content)
    for hashes, heading_text in headings:
        level = len(hashes)
        location = f'h{level}'
        _extract_promises_from_text(heading_text, location, promises, seen)

    # 콘텐츠 첫 줄 (제목이 마크다운 헤딩이 아닌 경우)
    lines = content.strip().split('\n')
    if lines:
        first_line = lines[0].strip()
        if not first_line.startswith('#'):
            _extract_promises_from_text(first_line, 'title', promises, seen)

    return promises


def _extract_promises_from_text(text: str, location: str, promises: list, seen: set):
    """텍스트에서 수치 약속 패턴을 추출합니다."""
    for pattern in _PROMISE_PATTERNS:
        for match in pattern.finditer(text):
            number = int(match.group(1))
            key = (location, number, match.group(0))
            if key not in seen and number > 0:
                seen.add(key)
                promises.append({
                    'text': match.group(0).strip(),
                    'promised_number': number,
                    'actual_count': 0,
                    'status': 'unknown',
                    'location': location,
                })


def _count_fulfillment(content: str, promise: dict) -> int:
    """약속된 수치에 대응하는 본문 항목 수를 셉니다."""
    counts = []

    # 1) 숫자 목록 카운팅 (1. 2. 3. / 1) 2) 3. / (1) (2))
    for pattern in _NUMBERED_LIST_PATTERNS:
        matches = pattern.findall(content)
        if matches:
            # 연속된 번호 시퀀스의 최대 개수
            numbers = [int(n) for n in matches]
            counts.append(_count_sequence(numbers))

    # 2) 한국어 서수 (첫째, 둘째, ...)
    ordinal_matches = _KOREAN_ORDINAL_PATTERN.findall(content)
    if ordinal_matches:
        ordinal_count = len(set(ordinal_matches))
        counts.append(ordinal_count)

    # 3) 소제목 (##, ###) 개수 — 약속이 h1이면 h2 카운트, h2이면 h3 카운트
    heading_counts = _count_sub_headings(content, promise)
    if heading_counts > 0:
        counts.append(heading_counts)

    # 가장 약속 숫자에 가까운 카운트 선택
    if not counts:
        return 0

    promised = promise['promised_number']
    return min(counts, key=lambda c: abs(c - promised))


def _count_sequence(numbers: list) -> int:
    """번호 목록에서 가장 긴 연속 시퀀스(또는 최대값)를 셉니다."""
    if not numbers:
        return 0

    # 1부터 시작하는 번호의 최대값 (즉, 몇 번까지 있는지)
    # 예: [1,2,3,1,2,3,4,5] → 5개 (가장 큰 시퀀스)
    max_num = max(numbers)

    # 단순히 고유 번호 개수도 계산
    unique_count = len(set(numbers))

    # 둘 중 더 큰 값 반환 (보수적 판단)
    return max(max_num, unique_count)


def _count_sub_headings(content: str, promise: dict) -> int:
    """약속 위치 기준으로 하위 소제목 수를 셉니다."""
    headings = _HEADING_PATTERN.findall(content)
    if not headings:
        return 0

    location = promise['location']

    # 제목 위치에 따라 카운트할 하위 레벨 결정
    if location in ('title', 'h1'):
        # h2 소제목 개수
        return sum(1 for h, _ in headings if len(h) == 2)
    elif location == 'h2':
        # h3 소제목 개수
        return sum(1 for h, _ in headings if len(h) == 3)
    elif location == 'h3':
        # h4 소제목 개수
        return sum(1 for h, _ in headings if len(h) == 4)

    return 0


def _determine_status(promised: int, actual: int) -> str:
    """약속 이행 상태를 판정합니다.

    - match: 정확히 일치
    - partial: 절반 이상 이행 (50% <= actual/promised < 100%)
    - mismatch: 절반 미만 또는 초과
    """
    if actual == promised:
        return 'match'

    if actual == 0:
        return 'mismatch'

    ratio = actual / promised
    if 0.5 <= ratio < 1.0:
        return 'partial'

    # 초과도 mismatch (약속보다 많은 것도 문제)
    return 'mismatch'


def _calculate_integrity_score(promises: list) -> float:
    """수치 약속 무결성 점수를 계산합니다 (0~100)."""
    if not promises:
        return 100.0

    scores = []
    for p in promises:
        status = p['status']
        if status == 'match':
            scores.append(100.0)
        elif status == 'partial':
            # 부분 이행 비율에 따라 점수 부여
            ratio = p['actual_count'] / p['promised_number']
            scores.append(ratio * 100.0)
        else:
            scores.append(0.0)

    score = sum(scores) / len(scores)
    # 0~100 범위 보장
    return max(0.0, min(100.0, round(score, 1)))


def _generate_suggestions(promises: list) -> list:
    """개선 제안을 생성합니다."""
    suggestions = []

    mismatches = [p for p in promises if p['status'] == 'mismatch']
    partials = [p for p in promises if p['status'] == 'partial']

    for p in mismatches:
        if p['actual_count'] == 0:
            suggestions.append(
                f'"{p["text"]}"에 대한 항목을 본문에 번호 목록으로 추가하세요.'
            )
        elif p['actual_count'] < p['promised_number']:
            diff = p['promised_number'] - p['actual_count']
            suggestions.append(
                f'"{p["text"]}": {diff}개 항목이 부족합니다 '
                f'(약속: {p["promised_number"]}개, 실제: {p["actual_count"]}개).'
            )
        else:
            diff = p['actual_count'] - p['promised_number']
            suggestions.append(
                f'"{p["text"]}": 약속보다 {diff}개 초과입니다 '
                f'(약속: {p["promised_number"]}개, 실제: {p["actual_count"]}개). '
                f'제목의 숫자를 수정하거나 항목을 조정하세요.'
            )

    for p in partials:
        diff = p['promised_number'] - p['actual_count']
        suggestions.append(
            f'"{p["text"]}": {diff}개 항목을 더 추가하면 약속이 완전히 이행됩니다 '
            f'(현재 {p["actual_count"]}/{p["promised_number"]}).'
        )

    if not suggestions:
        suggestions.append('모든 수치 약속이 정확히 이행되었습니다.')

    return suggestions
