"""
List Parallelism Checker 서비스

불릿/번호 목록 항목의 문법 형태, 시제, 길이가
일관적인지 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

# 목록 항목 추출 (마크다운 + 일반 목록)
_LIST_ITEM = re.compile(
    r'(?:^|\n)\s*(?:[-*•]\s+|\d+[.)]\s+)(.+)',
    re.MULTILINE,
)

# 한국어 문장 종결 패턴
_KO_ENDINGS = {
    'formal': re.compile(r'(?:합니다|입니다|됩니다|습니다|됩니다)[\s.]*$'),
    'informal': re.compile(r'(?:해요|예요|에요|세요|해주세요)[\s.]*$'),
    'plain': re.compile(r'(?:한다|된다|이다|있다|없다|하라|하자)[\s.]*$'),
    'noun_end': re.compile(r'(?:것|점|법|방법|사항|방식|예시|기능|도구)[\s.]*$'),
    'verb_stem': re.compile(r'(?:하기|되기|만들기|사용하기|설정하기|확인하기)[\s.]*$'),
}

# 영어 문장 시작 패턴
_EN_STARTS = {
    'imperative': re.compile(r'^(?:Use|Create|Add|Set|Run|Install|Check|Open|Click|Select|Enter|Type)\b', re.IGNORECASE),
    'gerund': re.compile(r'^(?:[A-Z][a-z]+ing)\b'),
    'noun': re.compile(r'^(?:The|A|An|This|That|Each|Every)\b', re.IGNORECASE),
    'how_to': re.compile(r'^(?:How\s+to)\b', re.IGNORECASE),
}


def _extract_lists(content: str) -> List[List[str]]:
    """연속된 목록 항목들을 그룹으로 추출합니다."""
    lines = content.split('\n')
    lists: List[List[str]] = []
    current: List[str] = []

    for line in lines:
        m = _LIST_ITEM.match(line.strip() if line.strip() else '')
        if m:
            current.append(m.group(1).strip())
        else:
            if len(current) >= 2:
                lists.append(current)
            current = []

    if len(current) >= 2:
        lists.append(current)

    return lists


def _classify_ending(item: str) -> str:
    """항목의 종결 유형을 분류합니다."""
    for name, pat in _KO_ENDINGS.items():
        if pat.search(item):
            return f'ko_{name}'
    for name, pat in _EN_STARTS.items():
        if pat.match(item):
            return f'en_{name}'
    return 'other'


def _check_length_consistency(items: List[str]) -> Dict:
    """항목 길이 일관성을 확인합니다."""
    lengths = [len(item) for item in items]
    if not lengths:
        return {'consistent': True, 'ratio': 0.0}

    avg = sum(lengths) / len(lengths)
    if avg == 0:
        return {'consistent': True, 'ratio': 0.0}

    max_deviation = max(abs(l - avg) / avg for l in lengths)
    return {
        'consistent': max_deviation <= 1.0,  # 2배 이상 차이나면 비일관
        'ratio': round(max_deviation, 2),
    }


def check_list_parallelism(content: str) -> dict:
    """목록 항목의 병렬 구조 일관성을 검사합니다.

    Returns:
        score, summary, parallelism_issues, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'total_lists': 0,
                'parallel_lists': 0,
                'non_parallel_lists': 0,
                'level': 'none',
            },
            'parallelism_issues': [],
            'suggestions': [],
        }

    lists = _extract_lists(content)

    if not lists:
        return {
            'score': 100.0,
            'summary': {
                'total_lists': 0,
                'parallel_lists': 0,
                'non_parallel_lists': 0,
                'level': 'none',
            },
            'parallelism_issues': [],
            'suggestions': [],
        }

    issues = []
    parallel_count = 0

    for lst in lists:
        endings = [_classify_ending(item) for item in lst]
        length_check = _check_length_consistency(lst)

        # 종결 유형 일관성 체크
        unique_endings = set(endings)
        dominant = max(set(endings), key=endings.count)
        dominant_ratio = endings.count(dominant) / len(endings)

        is_parallel = dominant_ratio >= 0.7 and length_check['consistent']

        if is_parallel:
            parallel_count += 1
        else:
            issue = {
                'items_preview': [item[:40] for item in lst[:4]],
                'item_count': len(lst),
                'ending_types': list(unique_endings),
                'length_consistent': length_check['consistent'],
            }
            if not length_check['consistent']:
                issue['length_deviation'] = length_check['ratio']
            issues.append(issue)

    total = len(lists)
    non_parallel = total - parallel_count

    # 레벨 판정
    if total == 0:
        level = 'none'
    elif non_parallel == 0:
        level = 'consistent'
    elif non_parallel / total <= 0.3:
        level = 'mostly_consistent'
    elif non_parallel / total <= 0.6:
        level = 'mixed'
    else:
        level = 'inconsistent'

    # 연속 점수 — 병렬 비율 기반
    if total == 0 or non_parallel == 0:
        score = 100.0
    else:
        parallel_ratio = parallel_count / total
        score = max(15.0, parallel_ratio * 90.0 + 10.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        total, parallel_count, non_parallel, level, issues
    )

    return {
        'score': score,
        'summary': {
            'total_lists': total,
            'parallel_lists': parallel_count,
            'non_parallel_lists': non_parallel,
            'level': level,
        },
        'parallelism_issues': issues[:5],
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, parallel: int,
                           non_parallel: int, level: str,
                           issues: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'consistent': '일관적',
        'mostly_consistent': '대부분 일관',
        'mixed': '혼재', 'inconsistent': '비일관',
    }
    suggestions.append(
        f'목록 병렬 구조: {level_labels.get(level, level)}. '
        f'전체 {total}개 목록 중 {parallel}개 일관, {non_parallel}개 비일관.'
    )

    if non_parallel > 0:
        suggestions.append(
            '목록 항목의 문법 형태(명사형/동사형/~합니다 체)를 통일하세요.'
        )

    for issue in issues[:2]:
        preview = ' / '.join(issue['items_preview'][:2])
        suggestions.append(
            f'비일관 목록 ({issue["item_count"]}개 항목): "{preview}..."'
        )

    return suggestions
