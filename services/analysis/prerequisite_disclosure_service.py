"""
Prerequisite Disclosure Checker 서비스

튜토리얼/가이드가 계정, 권한, 예산, 준비물, OS/버전 같은
사전조건을 빠뜨렸는지 확인합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# 튜토리얼/가이드 콘텐츠 신호
_TUTORIAL_SIGNALS = [
    re.compile(r'(?:튜토리얼|가이드|설치\s*방법|시작하기|따라하기|실습)', re.IGNORECASE),
    re.compile(r'(?:단계별|step\s*by\s*step|how\s*to|getting\s*started)', re.IGNORECASE),
    re.compile(r'(?:설정\s*(?:방법|하기)|구축\s*(?:방법|하기)|만들기)', re.IGNORECASE),
]

# 사전조건 카테고리별 패턴
_PREREQ_CATEGORIES = {
    'account': {
        'label': '계정/가입',
        'patterns': [
            re.compile(r'(?:계정|가입|회원|로그인|API\s*키|토큰|인증)', re.IGNORECASE),
            re.compile(r'\b(?:account|sign\s*up|register|login|API\s*key|token|auth)\b', re.IGNORECASE),
        ],
    },
    'permission': {
        'label': '권한/접근',
        'patterns': [
            re.compile(r'(?:권한|관리자|루트|sudo|admin|접근\s*(?:권한|레벨))', re.IGNORECASE),
            re.compile(r'\b(?:permission|admin|root|sudo|access\s*(?:level|rights?))\b', re.IGNORECASE),
        ],
    },
    'environment': {
        'label': 'OS/환경',
        'patterns': [
            re.compile(r'(?:운영\s*체제|OS|Windows|macOS|Linux|Ubuntu)', re.IGNORECASE),
            re.compile(r'(?:환경\s*(?:설정|구성|변수)|시스템\s*요구\s*사항)', re.IGNORECASE),
            re.compile(r'\b(?:operating\s*system|environment|system\s*requirements?)\b', re.IGNORECASE),
        ],
    },
    'version': {
        'label': '버전/의존성',
        'patterns': [
            re.compile(r'(?:버전|version)\s*(?:\d|:\s*\d)', re.IGNORECASE),
            re.compile(r'(?:Python|Node|Java|PHP|Ruby)\s*\d', re.IGNORECASE),
            re.compile(r'(?:npm|pip|apt|brew|yarn)\s+install', re.IGNORECASE),
            re.compile(r'\b(?:dependency|dependencies|prerequisite|require)\b', re.IGNORECASE),
        ],
    },
    'cost': {
        'label': '비용/예산',
        'patterns': [
            re.compile(r'(?:비용|요금|가격|무료|유료|구독|과금|결제)', re.IGNORECASE),
            re.compile(r'(?:\$\d|₩\d|원\/|달러)', re.IGNORECASE),
            re.compile(r'\b(?:cost|price|free|paid|subscription|billing|pricing)\b', re.IGNORECASE),
        ],
    },
    'tools': {
        'label': '도구/준비물',
        'patterns': [
            re.compile(r'(?:준비물|필요한\s*(?:것|도구|프로그램)|사전\s*(?:설치|준비))', re.IGNORECASE),
            re.compile(r'(?:(?:설치|다운로드)\s*(?:해야|필요|하세요))', re.IGNORECASE),
            re.compile(r'\b(?:prerequisites?|requirements?|you\'ll?\s+need|install\s+first)\b', re.IGNORECASE),
        ],
    },
    'knowledge': {
        'label': '사전지식',
        'patterns': [
            re.compile(r'(?:사전\s*(?:지식|경험|이해)|기본\s*(?:지식|개념)|배경\s*지식)', re.IGNORECASE),
            re.compile(r'(?:알고\s*있어야|이해하고\s*있어야|숙지)', re.IGNORECASE),
            re.compile(r'\b(?:prior\s+knowledge|familiarity\s+with|basic\s+understanding)\b', re.IGNORECASE),
        ],
    },
}

# 사전조건 섹션 헤딩 패턴
_PREREQ_HEADING_PATTERNS = [
    re.compile(r'(?:사전\s*(?:조건|준비|요구)|필수\s*(?:조건|요구)|요구\s*사항)', re.IGNORECASE),
    re.compile(r'(?:준비\s*(?:사항|물)|시작\s*전\s*(?:에|준비))', re.IGNORECASE),
    re.compile(r'\b(?:prerequisites?|requirements?|before\s+you\s+(?:begin|start)|what\s+you\s+need)\b', re.IGNORECASE),
]

_HEADING_RE = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)


def _count_matches(content: str, patterns: list) -> int:
    return sum(len(p.findall(content)) for p in patterns)


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


_EMPTY_RESULT = {
    'score': 100.0,
    'summary': {
        'is_tutorial_content': False,
        'has_prereq_section': False,
        'prereqs_found': [],
        'prereqs_implied': [],
        'completeness_ratio': 0.0,
        'level': 'none',
    },
    'missing_prereqs': [],
    'suggestions': [],
}


def _scan_prereq_categories(content: str) -> tuple:
    """카테고리별 사전조건 존재 여부와 암시적 조건을 탐지합니다.

    Returns:
        (prereqs_found, prereqs_implied)
    """
    prereqs_found = []
    prereqs_implied = []

    for cat_name, cat_info in _PREREQ_CATEGORIES.items():
        if _has_pattern(content, cat_info['patterns']):
            prereqs_found.append(cat_name)

    if re.search(r'```[\s\S]*?(?:pip install|npm install|apt install|brew install)[\s\S]*?```', content):
        if 'version' not in prereqs_found:
            prereqs_implied.append('version')
        if 'tools' not in prereqs_found:
            prereqs_implied.append('tools')

    return prereqs_found, prereqs_implied


def _compute_prereq_score(is_tutorial: bool, has_prereq_section: bool,
                           prereqs_found: List[str], completeness: float) -> tuple:
    """사전조건 공시 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if not is_tutorial:
        level = 'none'
    elif has_prereq_section and completeness >= 50:
        level = 'good'
    elif has_prereq_section or completeness >= 30:
        level = 'fair'
    elif len(prereqs_found) > 0:
        level = 'partial'
    else:
        level = 'missing'

    if not is_tutorial:
        score = 100.0
    else:
        score = 30.0 + (completeness / 100.0 * 60.0)
        if has_prereq_section:
            score += 10.0

    score = round(max(0.0, min(100.0, score)), 1)
    return score, level


def check_prerequisite_disclosure(content: str) -> dict:
    """튜토리얼/가이드의 사전조건 공시를 점검합니다.

    Returns:
        score, summary, suggestions, missing_prereqs를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        is_tutorial = _count_matches(content, _TUTORIAL_SIGNALS) >= 2

        headings = _HEADING_RE.findall(content)
        has_prereq_section = any(
            _has_pattern(h, _PREREQ_HEADING_PATTERNS) for h in headings
        )

        prereqs_found, prereqs_implied = _scan_prereq_categories(content)
        completeness = round(len(prereqs_found) / max(len(_PREREQ_CATEGORIES), 1) * 100, 1)
        score, level = _compute_prereq_score(is_tutorial, has_prereq_section, prereqs_found, completeness)

        missing = []
        if is_tutorial:
            for cat_name, cat_info in _PREREQ_CATEGORIES.items():
                if cat_name not in prereqs_found and cat_name in prereqs_implied:
                    missing.append({
                        'category': cat_name,
                        'label': cat_info['label'],
                        'reason': '본문에 암시되어 있으나 명시적 공시 없음',
                    })

        suggestions = _generate_suggestions(
            is_tutorial, has_prereq_section, prereqs_found,
            prereqs_implied, missing, level
        )

        return {
            'score': score,
            'summary': {
                'is_tutorial_content': is_tutorial,
                'has_prereq_section': has_prereq_section,
                'prereqs_found': prereqs_found,
                'prereqs_implied': prereqs_implied,
                'completeness_ratio': completeness,
                'level': level,
            },
            'missing_prereqs': missing,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(is_tutorial: bool, has_section: bool,
                           found: List[str], implied: List[str],
                           missing: List[Dict], level: str) -> List[str]:
    suggestions = []

    if not is_tutorial:
        suggestions.append('튜토리얼/가이드 콘텐츠가 아닌 것으로 판단됩니다.')
        return suggestions

    level_labels = {
        'good': '양호', 'fair': '보통',
        'partial': '부분적', 'missing': '부족',
    }
    suggestions.append(
        f'사전조건 공시: {level_labels.get(level, level)} '
        f'({len(found)}/{len(_PREREQ_CATEGORIES)} 카테고리).'
    )

    if not has_section:
        suggestions.append(
            '"사전 준비" 또는 "Prerequisites" 섹션을 글 상단에 추가하세요.'
        )

    for m in missing[:3]:
        suggestions.append(
            f'{m["label"]}({m["category"]}): {m["reason"]}. 명시적으로 안내하세요.'
        )

    if not found and not implied:
        suggestions.append(
            '사전조건(계정, 버전, 도구 등)을 독자가 미리 준비할 수 있도록 안내하세요.'
        )

    return suggestions
