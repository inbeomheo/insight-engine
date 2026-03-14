"""
Definition Gap Detector 서비스

전문 용어나 약어가 정의 없이 처음 등장하는
구간을 찾아 독자 이해도 저하 지점을 표시합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

# 약어 패턴 (2~6자 대문자)
_ACRONYM = re.compile(r'\b[A-Z]{2,6}(?![A-Za-z])')

# 전문 용어 패턴 (한국어)
_KO_TECHNICAL = re.compile(
    r'(?:레이턴시|스루풋|쓰로틀링|페이로드|미들웨어|프레임워크|'
    r'리팩토링|디커플링|마이크로서비스|오케스트레이션|'
    r'프로비저닝|인스턴스|컨테이너|클러스터|'
    r'캐싱|파이프라인|웹훅|폴링|소켓|'
    r'디버깅|프로파일링|벤치마킹|'
    r'시리얼라이제이션|디시리얼라이제이션)',
    re.IGNORECASE,
)

# 영어 전문 용어
_EN_TECHNICAL = re.compile(
    r'\b(?:latency|throughput|throttling|payload|middleware|'
    r'refactoring|decoupling|microservice|orchestration|'
    r'provisioning|containerization|serialization|deserialization|'
    r'idempotent|polymorphism|encapsulation|abstraction|'
    r'webhook|polling|sharding|partitioning|replication)\b',
    re.IGNORECASE,
)

# 정의 패턴 (용어 뒤에 정의가 있는 경우)
_DEFINITION_PATTERNS = [
    re.compile(r'(?:이란|란|이라\s*함은|이라고\s*하|라고\s*부르|의미합|의미하|뜻하)', re.IGNORECASE),
    re.compile(r'(?:즉,|다시\s*말해|쉽게\s*말하면|간단히\s*말하면)', re.IGNORECASE),
    re.compile(r'(?:\(.*?(?:이하|약칭|줄여서).*?\))', re.IGNORECASE),
    re.compile(r'\b(?:i\.e\.|means?|refers?\s+to|defined?\s+as|known\s+as|stands?\s+for)', re.IGNORECASE),
    re.compile(r'\(.*?(?:aka|a\.k\.a\.|also\s+known)\b.*?\)', re.IGNORECASE),
]

# 괄호 정의 (약어 뒤 괄호로 풀어쓰기 또는 풀어쓴 뒤 괄호로 약어)
_PAREN_DEFINITION = re.compile(
    r'(?:[A-Z]{2,6}\s*\([^)]+\))|(?:\([A-Z]{2,6}\))',
    re.IGNORECASE,
)

# 흔한 약어 (정의 불필요)
_COMMON_ACRONYMS = {
    'API', 'URL', 'HTML', 'CSS', 'JS', 'JSON', 'XML', 'HTTP', 'HTTPS',
    'SQL', 'DB', 'UI', 'UX', 'OS', 'CPU', 'RAM', 'GPU', 'SSD', 'HDD',
    'PDF', 'CSV', 'PNG', 'JPG', 'GIF', 'SVG', 'MP4', 'MP3',
    'ID', 'IP', 'DNS', 'SSH', 'FTP', 'TCP', 'UDP',
    'CI', 'CD', 'PR', 'QA', 'MVP', 'SDK', 'CLI', 'GUI',
    'AI', 'ML', 'NLP', 'LLM', 'GPT',
    'OK', 'FAQ', 'TODO', 'TBD', 'WIP', 'FYI', 'ASAP',
}


def _find_terms(content: str) -> List[Dict]:
    """전문 용어와 약어를 찾습니다."""
    terms = []
    seen = set()

    # 약어 찾기
    for m in _ACRONYM.finditer(content):
        text = m.group()
        if text not in _COMMON_ACRONYMS and text not in seen:
            seen.add(text)
            terms.append({
                'term': text,
                'type': 'acronym',
                'position': m.start(),
            })

    # 한국어 전문 용어
    for m in _KO_TECHNICAL.finditer(content):
        text = m.group()
        if text.lower() not in seen:
            seen.add(text.lower())
            terms.append({
                'term': text,
                'type': 'technical_ko',
                'position': m.start(),
            })

    # 영어 전문 용어
    for m in _EN_TECHNICAL.finditer(content):
        text = m.group()
        if text.lower() not in seen:
            seen.add(text.lower())
            terms.append({
                'term': text,
                'type': 'technical_en',
                'position': m.start(),
            })

    return terms


def _has_definition_nearby(content: str, term: str, position: int) -> bool:
    """용어 주변(±200자)에 정의가 있는지 확인합니다."""
    start = max(0, position - 100)
    end = min(len(content), position + len(term) + 200)
    context = content[start:end]

    # 괄호 정의 확인
    if _PAREN_DEFINITION.search(context):
        return True

    # 정의 패턴 확인
    return any(p.search(context) for p in _DEFINITION_PATTERNS)


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'total_terms': 0, 'defined_terms': 0,
        'undefined_terms': 0, 'level': 'none',
    },
    'undefined_terms': [],
    'suggestions': [],
}


def _check_definitions(content: str, terms: list) -> tuple:
    """용어별 정의 존재 여부를 확인합니다.

    Returns:
        (defined_count, undefined_items)
    """
    defined_count = 0
    undefined_items = []

    for term in terms:
        if _has_definition_nearby(content, term['term'], term['position']):
            defined_count += 1
        else:
            undefined_items.append({
                'term': term['term'],
                'type': term['type'],
            })

    return defined_count, undefined_items


def _compute_gap_score(total: int, defined_count: int, undefined_count: int) -> tuple:
    """정의 갭 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if undefined_count == 0:
        level = 'all_defined'
    elif undefined_count <= 2:
        level = 'minor_gaps'
    elif undefined_count / total <= 0.5:
        level = 'moderate_gaps'
    else:
        level = 'many_gaps'

    score = (defined_count / total * 100.0) if total > 0 else 100.0
    if undefined_count > 0:
        score -= min(20.0, undefined_count ** 1.2 * 3.0)

    return round(max(0.0, min(100.0, score)), 1), level


def detect_definition_gaps(content: str) -> dict:
    """정의 없는 전문 용어/약어를 탐지합니다.

    Returns:
        score, summary, undefined_terms, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    terms = _find_terms(content)
    if not terms:
        return dict(_EMPTY_RESULT)

    defined_count, undefined_items = _check_definitions(content, terms)
    total = len(terms)
    undefined_count = total - defined_count
    score, level = _compute_gap_score(total, defined_count, undefined_count)

    return {
        'score': score,
        'summary': {
            'total_terms': total, 'defined_terms': defined_count,
            'undefined_terms': undefined_count, 'level': level,
        },
        'undefined_terms': undefined_items[:10],
        'suggestions': _generate_suggestions(
            total, defined_count, undefined_count, level, undefined_items
        ),
    }


def _generate_suggestions(total: int, defined: int, undefined: int,
                           level: str, items: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'all_defined': '모두 정의됨',
        'minor_gaps': '경미한 누락', 'moderate_gaps': '보통 누락',
        'many_gaps': '많은 누락',
    }
    suggestions.append(
        f'용어 정의: {level_labels.get(level, level)}. '
        f'전문 용어 {total}개 중 {defined}개 정의됨, {undefined}개 미정의.'
    )

    if undefined > 0:
        suggestions.append(
            '전문 용어나 약어를 처음 사용할 때 '
            '"~(이하 XX)" 또는 "XX란 ~을 의미합니다" 형태로 정의하세요.'
        )

    for item in items[:3]:
        type_label = {'acronym': '약어', 'technical_ko': '전문용어',
                      'technical_en': '전문용어'}.get(item['type'], '용어')
        suggestions.append(
            f'미정의 {type_label}: "{item["term"]}" — 첫 등장 시 정의를 추가하세요.'
        )

    return suggestions
