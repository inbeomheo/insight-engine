"""
Step Verification Coverage Analyzer 서비스

가이드형 문서에서 각 단계 뒤에 확인 기준이나
예상 결과가 있는지 점검합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

# 단계 제목 패턴
_STEP_PATTERNS = [
    re.compile(r'(?:^|\n)\s*(?:#+\s*)?(?:단계|스텝|Step)\s*\d+', re.IGNORECASE),
    re.compile(r'(?:^|\n)\s*\d+[.)]\s+.+', re.MULTILINE),
    re.compile(r'(?:^|\n)\s*(?:첫\s*번째|두\s*번째|세\s*번째|네\s*번째|다섯\s*번째)', re.IGNORECASE),
    re.compile(r'(?:^|\n)\s*(?:First|Second|Third|Fourth|Fifth)\b', re.IGNORECASE),
]

# 검증/확인 기준 패턴
_VERIFICATION_PATTERNS = [
    re.compile(r'(?:확인|검증|점검|체크)(?:\s*(?:하세요|합니다|방법|사항))', re.IGNORECASE),
    re.compile(r'(?:예상\s*결과|기대\s*결과|출력\s*결과|결과\s*화면)', re.IGNORECASE),
    re.compile(r'(?:성공\s*(?:하면|시|했으면)|정상\s*(?:작동|동작))', re.IGNORECASE),
    re.compile(r'(?:다음과\s*같이\s*(?:표시|나타|출력))', re.IGNORECASE),
    re.compile(r'(?:올바르게|제대로|정확히)\s*(?:설정|설치|작동|실행)', re.IGNORECASE),
    re.compile(r'\b(?:verify|check|confirm|ensure|validate|expected\s*(?:output|result))\b', re.IGNORECASE),
    re.compile(r'\b(?:you\s+should\s+see|if\s+successful|output\s+should)\b', re.IGNORECASE),
    re.compile(r'```[\s\S]*?```'),  # 코드 블록 (출력 예시로 간주)
]

# 경고/주의 패턴 (부가 검증 신호)
_WARNING_PATTERNS = [
    re.compile(r'(?:주의|경고|참고|팁|노트|힌트)', re.IGNORECASE),
    re.compile(r'\b(?:Note|Warning|Tip|Caution|Important)\b', re.IGNORECASE),
    re.compile(r'(?:⚠|💡|📌|❗|✅)', re.IGNORECASE),
]


def _extract_steps(content: str) -> List[Dict]:
    """문서에서 단계 항목을 추출합니다."""
    steps = []
    seen_positions = set()

    for pat in _STEP_PATTERNS:
        for m in pat.finditer(content):
            pos = m.start()
            # 가까운 위치(20자 이내) 중복 제거
            if any(abs(pos - p) < 20 for p in seen_positions):
                continue
            seen_positions.add(pos)
            steps.append({
                'text': m.group().strip()[:60],
                'position': pos,
            })

    steps.sort(key=lambda s: s['position'])
    return steps


def _has_verification(text: str) -> bool:
    """텍스트에 검증/확인 표현이 있는지 확인합니다."""
    return any(p.search(text) for p in _VERIFICATION_PATTERNS)


def _has_warning(text: str) -> bool:
    """경고/참고 표현이 있는지 확인합니다."""
    return any(p.search(text) for p in _WARNING_PATTERNS)


def analyze_step_verification_coverage(content: str) -> dict:
    """가이드 문서의 단계별 검증 기준 존재 여부를 점검합니다.

    Returns:
        score, summary, step_details, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'total_steps': 0,
                'verified_steps': 0,
                'unverified_steps': 0,
                'coverage_ratio': 0.0,
                'level': 'none',
            },
            'step_details': [],
            'suggestions': [],
        }

    steps = _extract_steps(content)

    if not steps:
        return {
            'score': 100.0,
            'summary': {
                'total_steps': 0,
                'verified_steps': 0,
                'unverified_steps': 0,
                'coverage_ratio': 0.0,
                'level': 'none',
            },
            'step_details': [],
            'suggestions': [],
        }

    # 각 단계 뒤의 텍스트에서 검증 표현 탐색
    step_details = []
    verified_count = 0

    for i, step in enumerate(steps):
        # 현재 단계와 다음 단계 사이의 텍스트
        start = step['position']
        end = steps[i + 1]['position'] if i + 1 < len(steps) else len(content)
        section_text = content[start:end]

        has_ver = _has_verification(section_text)
        has_warn = _has_warning(section_text)

        if has_ver:
            verified_count += 1

        step_details.append({
            'step': step['text'][:50],
            'has_verification': has_ver,
            'has_warning': has_warn,
        })

    total = len(steps)
    unverified = total - verified_count
    coverage = round(verified_count / max(total, 1) * 100, 1)

    # 레벨 판정
    if coverage >= 80:
        level = 'thorough'
    elif coverage >= 50:
        level = 'partial'
    elif coverage >= 20:
        level = 'minimal'
    else:
        level = 'missing'

    # 연속 점수 — coverage 비율 기반
    score = 20.0 + (coverage / 100.0 * 75.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        total, verified_count, unverified, coverage, level, step_details
    )

    return {
        'score': score,
        'summary': {
            'total_steps': total,
            'verified_steps': verified_count,
            'unverified_steps': unverified,
            'coverage_ratio': coverage,
            'level': level,
        },
        'step_details': step_details[:10],
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, verified: int,
                           unverified: int, coverage: float,
                           level: str, details: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'thorough': '철저',
        'partial': '부분적', 'minimal': '최소', 'missing': '없음',
    }
    suggestions.append(
        f'단계 검증 커버리지: {level_labels.get(level, level)}. '
        f'전체 {total}단계 중 {verified}단계에 검증 기준 있음 ({coverage}%).'
    )

    if unverified > 0:
        suggestions.append(
            '각 단계 뒤에 "확인: ~가 표시되면 성공" 또는 '
            '"예상 결과: ~" 형태의 검증 기준을 추가하세요.'
        )

    missing_steps = [d for d in details if not d['has_verification']]
    for step in missing_steps[:2]:
        suggestions.append(
            f'검증 없는 단계: "{step["step"][:40]}" — 확인 방법을 추가하세요.'
        )

    return suggestions
