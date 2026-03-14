"""
Instruction Sequence Validator 서비스

튜토리얼/가이드 콘텐츠에서 절차(순서형 지시)의 논리적 일관성을 검증합니다.
번호 매기기 오류, 순서 건너뛰기, 불완전한 절차를 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# 마크다운 헤딩
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 번호 매기기 패턴
_NUMBERED_STEP_RE = re.compile(r'^\s*(\d+)[.)]\s+(.+)', re.MULTILINE)

# "Step N" 패턴
_STEP_N_RE = re.compile(r'(?:Step|단계)\s*(\d+)\s*[:.]\s*(.+)', re.IGNORECASE)

# 순서 표현 (한국어)
_ORDINAL_KO = re.compile(r'(첫째|둘째|셋째|넷째|다섯째|여섯째|일곱째|여덟째|아홉째|열째)')
_ORDINAL_KO_MAP = {
    '첫째': 1, '둘째': 2, '셋째': 3, '넷째': 4, '다섯째': 5,
    '여섯째': 6, '일곱째': 7, '여덟째': 8, '아홉째': 9, '열째': 10,
}

# 순서 표현 (영어)
_ORDINAL_EN = re.compile(r'\b(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\b', re.IGNORECASE)
_ORDINAL_EN_MAP = {
    'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
    'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
}


def _find_numbered_sequences(content: str) -> List[Dict]:
    """번호 매기기 시퀀스를 찾고 검증합니다."""
    sequences = []
    current_seq = []
    last_num = 0

    for match in _NUMBERED_STEP_RE.finditer(content):
        num = int(match.group(1))
        text = match.group(2).strip()

        if num == 1 and current_seq:
            sequences.append(current_seq)
            current_seq = []
            last_num = 0

        current_seq.append({'number': num, 'text': text[:80], 'expected': last_num + 1})
        last_num = num

    if current_seq:
        sequences.append(current_seq)
    return sequences


def _find_step_sequences(content: str) -> List[Dict]:
    """Step N 패턴 시퀀스를 찾습니다."""
    steps = []
    for match in _STEP_N_RE.finditer(content):
        num = int(match.group(1))
        text = match.group(2).strip()
        steps.append({'number': num, 'text': text[:80]})
    return steps


def _find_ordinal_sequences(content: str) -> List[Dict]:
    """순서 표현 시퀀스를 찾습니다."""
    ordinals = []
    for match in _ORDINAL_KO.finditer(content):
        word = match.group(1)
        ordinals.append({'word': word, 'number': _ORDINAL_KO_MAP.get(word, 0)})
    for match in _ORDINAL_EN.finditer(content):
        word = match.group(1).lower()
        ordinals.append({'word': match.group(1), 'number': _ORDINAL_EN_MAP.get(word, 0)})
    return ordinals


def _validate_sequence(items: List[Dict]) -> List[Dict]:
    """시퀀스의 오류를 검증합니다."""
    issues = []
    if not items:
        return issues

    nums = [i['number'] for i in items]

    # 시작이 1이 아닌 경우
    if nums[0] != 1:
        issues.append({
            'type': 'wrong_start',
            'detail': f'시퀀스가 {nums[0]}에서 시작 (1부터 시작해야 함)',
        })

    # 건너뛰기 감지
    for i in range(1, len(nums)):
        if nums[i] != nums[i - 1] + 1:
            if nums[i] > nums[i - 1] + 1:
                issues.append({
                    'type': 'skip',
                    'detail': f'{nums[i - 1]} → {nums[i]} (중간 단계 누락)',
                })
            elif nums[i] <= nums[i - 1]:
                issues.append({
                    'type': 'duplicate_or_reverse',
                    'detail': f'{nums[i - 1]} → {nums[i]} (중복 또는 역순)',
                })

    return issues


_EMPTY_RESULT = {
    'sequences': [],
    'ordinals': [],
    'issues': [],
    'summary': {'total_sequences': 0, 'total_steps': 0,
                'total_issues': 0, 'has_instructions': False},
    'score': 100.0,
    'suggestions': [],
}


def _collect_all_issues(numbered: list, step_items: list, ordinals: list) -> List[Dict]:
    """모든 시퀀스 유형에서 이슈를 수집합니다."""
    all_issues = []
    for seq in numbered:
        all_issues.extend(_validate_sequence(seq))
    if step_items:
        all_issues.extend(_validate_sequence(step_items))
    if ordinals:
        all_issues.extend(_validate_sequence(ordinals))
    return all_issues


def _summarize_sequences(numbered: list) -> List[Dict]:
    """번호 시퀀스를 요약합니다."""
    summaries = []
    for i, seq in enumerate(numbered):
        nums = [s['number'] for s in seq]
        summaries.append({
            'index': i + 1,
            'steps': len(seq),
            'range': f'{nums[0]}-{nums[-1]}' if nums else '',
        })
    return summaries


def validate_instruction_sequence(content: str) -> dict:
    """절차의 논리적 일관성을 검증합니다.

    Returns:
        sequences, ordinals, issues, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    numbered = _find_numbered_sequences(content)
    step_items = _find_step_sequences(content)
    ordinals = _find_ordinal_sequences(content)

    all_issues = _collect_all_issues(numbered, step_items, ordinals)
    total_steps = sum(len(s) for s in numbered) + len(step_items) + len(ordinals)
    has_instructions = total_steps > 0
    total_issues = len(all_issues)

    if not has_instructions or total_issues == 0:
        score = 100.0
    else:
        score = round(max(0.0, 100.0 - total_issues * 20.0), 1)

    return {
        'sequences': _summarize_sequences(numbered),
        'ordinals': ordinals,
        'issues': all_issues,
        'summary': {
            'total_sequences': len(numbered),
            'total_steps': total_steps,
            'total_issues': total_issues,
            'has_instructions': has_instructions,
        },
        'score': score,
        'suggestions': _generate_suggestions(all_issues, has_instructions, total_steps),
    }


def _generate_suggestions(issues: List[Dict], has_inst: bool, steps: int) -> List[str]:
    suggestions = []
    if not has_inst:
        return suggestions
    if not issues:
        suggestions.append(f'절차가 올바르게 구성되어 있습니다 ({steps}단계).')
        return suggestions

    for issue in issues[:3]:
        suggestions.append(f'{issue["type"]}: {issue["detail"]}')

    if len(issues) > 1:
        suggestions.append('절차 번호를 1부터 순서대로 다시 확인하세요.')
    return suggestions
