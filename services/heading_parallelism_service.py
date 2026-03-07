"""
헤딩 병렬 구조 검사 서비스

마크다운 헤딩의 동일 레벨 내 문법 형태 일관성을 검사합니다.
같은 레벨의 헤딩이 명사구, 질문형, 명령형 등 서로 다른 형태로
혼용되면 비일관성으로 표시하고 개선 제안을 제공합니다.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# --- 문법 형태 판별 패턴 ---

# 숫자로 시작하는 패턴 (예: "1.", "Step 1", "단계 1")
_NUMBERED_RE = re.compile(
    r'^(?:\d+[\.\)\-]|step\s+\d+|단계\s*\d+)',
    re.IGNORECASE,
)

# 질문형 패턴 (한국어 + 영어)
_QUESTION_RE = re.compile(
    r'(?:\?$|인가요|할까요|일까요|인가\?|뭘까|무엇|어떻게|왜\s|얼마나|언제\s|어디서|누가\s|^how\s|^what\s|^why\s|^when\s|^where\s|^who\s|^is\s|^are\s|^can\s|^do\s|^does\s|^should\s)',
    re.IGNORECASE,
)

# 명령형 패턴 (한국어 + 영어)
_IMPERATIVE_KO_SUFFIXES = (
    '하세요', '하라', '하십시오', '합시다', '해보세요', '해라',
    '보세요', '드세요', '으세요', '세요',
)
_IMPERATIVE_EN_RE = re.compile(
    r'^(?:use|create|build|make|add|remove|delete|set|get|run|start|stop|install|deploy|configure|check|test|try|avoid|write|read|open|close|update|define|implement|apply|enable|disable)\b',
    re.IGNORECASE,
)

# 동명사형 패턴 (한국어 "~하기", 영어 "~ing")
_GERUND_KO_RE = re.compile(r'하기$|만들기$|쓰기$|읽기$|보기$|찾기$|알기$|살기$|짓기$')
_GERUND_EN_RE = re.compile(r'ing\b', re.IGNORECASE)


def check_heading_parallelism(content: str) -> dict:
    """마크다운 헤딩의 동일 레벨 내 문법 형태 일관성을 검사합니다.

    Args:
        content: 마크다운 콘텐츠

    Returns:
        {
            "headings": [{"text": str, "level": int, "form": str}],
            "groups": {level: {"forms": dict, "is_parallel": bool, "dominant_form": str}},
            "parallelism_score": float,  # 0-100
            "issues": [{"level": int, "mismatched_heading": str, "expected_form": str, "actual_form": str}],
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return _empty_result()

    # 1) 헤딩 추출
    headings = _extract_headings(content)

    if not headings:
        return _empty_result(headings=[])

    # 2) 레벨별 그룹화
    groups = _group_by_level(headings)

    # 3) 비일관성 검출
    issues = _find_issues(headings, groups)

    # 4) 점수 계산
    score = _calculate_score(headings, groups)

    # 5) 개선 제안 생성
    suggestions = _generate_suggestions(groups, issues)

    return {
        'headings': headings,
        'groups': groups,
        'parallelism_score': score,
        'issues': issues,
        'suggestions': suggestions,
    }


def _empty_result(headings=None):
    """빈 콘텐츠 또는 헤딩 없는 경우의 기본 반환값."""
    return {
        'headings': headings if headings is not None else [],
        'groups': {},
        'parallelism_score': 100.0,
        'issues': [],
        'suggestions': [],
    }


def _extract_headings(content: str) -> list:
    """마크다운 헤딩(#, ##, ###)을 추출하여 레벨 + 형태를 분류합니다."""
    headings = []
    for line in content.splitlines():
        line = line.strip()
        match = re.match(r'^(#{1,3})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            form = _classify_form(text)
            headings.append({
                'text': text,
                'level': level,
                'form': form,
            })
    return headings


def _classify_form(text: str) -> str:
    """헤딩 텍스트의 문법 형태를 분류합니다.

    판별 우선순위: numbered → question → imperative → gerund → noun_phrase
    """
    stripped = text.strip()

    # 1) 숫자로 시작
    if _NUMBERED_RE.search(stripped):
        return 'numbered'

    # 2) 질문형
    if _QUESTION_RE.search(stripped):
        return 'question'

    # 3) 명령형 (한국어)
    if any(stripped.endswith(suffix) for suffix in _IMPERATIVE_KO_SUFFIXES):
        return 'imperative'

    # 4) 명령형 (영어 — 동사 원형으로 시작)
    if _IMPERATIVE_EN_RE.match(stripped):
        return 'imperative'

    # 5) 동명사형 (한국어)
    if _GERUND_KO_RE.search(stripped):
        return 'gerund'

    # 6) 동명사형 (영어 — "~ing"으로 끝나는 단어 포함)
    # 단어 단위로 마지막 단어가 -ing 인지 확인
    words = stripped.split()
    if words:
        last_word = words[-1].rstrip('.,;:!?')
        if _GERUND_EN_RE.search(last_word) and len(last_word) > 3:
            return 'gerund'
        # 첫 단어가 -ing 형태 (예: "Building APIs")
        first_word = words[0].rstrip('.,;:!?')
        if _GERUND_EN_RE.search(first_word) and len(first_word) > 3:
            return 'gerund'

    # 7) 기본: 명사구
    return 'noun_phrase'


def _group_by_level(headings: list) -> dict:
    """헤딩을 레벨별로 그룹화하고 형태 분포를 계산합니다."""
    level_forms = {}  # {level: [form1, form2, ...]}

    for h in headings:
        level = h['level']
        if level not in level_forms:
            level_forms[level] = []
        level_forms[level].append(h['form'])

    groups = {}
    for level, forms in level_forms.items():
        counter = Counter(forms)
        # 지배적 형태: 가장 빈번한 형태
        dominant_form = counter.most_common(1)[0][0]
        is_parallel = len(counter) == 1  # 형태가 하나뿐이면 일관적

        groups[level] = {
            'forms': dict(counter),
            'is_parallel': is_parallel,
            'dominant_form': dominant_form,
        }

    return groups


def _find_issues(headings: list, groups: dict) -> list:
    """지배적 형태와 다른 헤딩을 비일관성 이슈로 수집합니다."""
    issues = []
    for h in headings:
        level = h['level']
        group = groups[level]
        if not group['is_parallel'] and h['form'] != group['dominant_form']:
            issues.append({
                'level': level,
                'mismatched_heading': h['text'],
                'expected_form': group['dominant_form'],
                'actual_form': h['form'],
            })
    return issues


def _calculate_score(headings: list, groups: dict) -> float:
    """병렬 구조 점수를 계산합니다 (0-100).

    각 레벨의 일관성 비율을 가중 평균합니다.
    가중치는 해당 레벨의 헤딩 수입니다.
    """
    if not headings:
        return 100.0

    total_headings = 0
    consistent_headings = 0

    for level, group in groups.items():
        forms = group['forms']
        level_total = sum(forms.values())
        dominant_count = max(forms.values())

        total_headings += level_total
        consistent_headings += dominant_count

    if total_headings == 0:
        return 100.0

    return round((consistent_headings / total_headings) * 100, 1)


# 형태 이름 한국어 매핑
_FORM_LABELS = {
    'noun_phrase': '명사구',
    'question': '질문형',
    'imperative': '명령형',
    'gerund': '동명사형',
    'numbered': '번호형',
}


def _generate_suggestions(groups: dict, issues: list) -> list:
    """비일관성에 대한 개선 제안을 생성합니다."""
    suggestions = []

    if not issues:
        if groups:
            suggestions.append('모든 레벨의 헤딩이 일관된 형태를 유지하고 있습니다.')
        return suggestions

    # 레벨별 이슈 집계
    level_issues = {}
    for issue in issues:
        lvl = issue['level']
        if lvl not in level_issues:
            level_issues[lvl] = []
        level_issues[lvl].append(issue)

    for level, level_issue_list in level_issues.items():
        group = groups[level]
        dominant = group['dominant_form']
        dominant_label = _FORM_LABELS.get(dominant, dominant)
        prefix = '#' * level

        suggestions.append(
            f'{prefix} 레벨 헤딩에서 {len(level_issue_list)}개가 '
            f'지배적 형태({dominant_label})와 다릅니다. '
            f'통일을 권장합니다.'
        )

        for issue in level_issue_list:
            actual_label = _FORM_LABELS.get(issue['actual_form'], issue['actual_form'])
            suggestions.append(
                f'  - "{issue["mismatched_heading"]}" → '
                f'{actual_label}에서 {dominant_label}(으)로 변경 권장'
            )

    return suggestions
