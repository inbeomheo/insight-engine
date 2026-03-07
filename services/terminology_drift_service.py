"""
Terminology Drift Analyzer 서비스

같은 개념을 섹션마다 다른 용어로 바꿔 부르며
생기는 혼선을 감지합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
from collections import Counter

_HEADING = re.compile(r'^#{1,6}\s+(.+)', re.MULTILINE)
_WORD_SPLIT = re.compile(r'[가-힣]+|[a-zA-Z]+(?:-[a-zA-Z]+)*', re.IGNORECASE)

# 동의어 그룹 (같은 개념을 다르게 부르는 표현)
_SYNONYM_GROUPS = [
    {'사용자', '유저', '이용자', '고객', '회원'},
    {'서버', '백엔드', '서버단', '서버측'},
    {'클라이언트', '프론트엔드', '프론트', '클라이언트측'},
    {'데이터베이스', 'DB', '디비', '데이터 저장소'},
    {'API', '인터페이스', '엔드포인트', '접점'},
    {'함수', '메서드', '메소드', '펑션'},
    {'변수', '파라미터', '매개변수', '인자', '인수'},
    {'설치', '인스톨', '셋업', '설정'},
    {'삭제', '제거', '디리트'},
    {'생성', '만들기', '크리에이트', '추가'},
    {'수정', '변경', '편집', '업데이트', '갱신'},
    {'실행', '구동', '런', '시작'},
    {'배포', '디플로이', '릴리스', '릴리즈'},
    {'저장소', '레포', '리포지토리', '레포지토리'},
    {'컨테이너', '도커', '컨테이너화'},
    {'인증', '로그인', '사인인', '로그인'},
    {'권한', '퍼미션', '접근 권한', '액세스 권한'},
    {'오류', '에러', '버그', '결함'},
    {'테스트', '검증', '시험', '검사'},
    {'문서', '문서화', '도큐먼트', '도큐먼테이션'},
]

# 영어 동의어 그룹
_EN_SYNONYM_GROUPS = [
    {'user', 'customer', 'client', 'member', 'end-user'},
    {'server', 'backend', 'back-end', 'server-side'},
    {'function', 'method', 'routine', 'procedure'},
    {'variable', 'parameter', 'argument', 'param'},
    {'install', 'setup', 'set-up', 'configure'},
    {'delete', 'remove', 'drop', 'erase'},
    {'create', 'add', 'generate', 'make'},
    {'update', 'modify', 'edit', 'change'},
    {'deploy', 'release', 'publish', 'ship'},
    {'repository', 'repo', 'codebase'},
    {'error', 'bug', 'defect', 'fault', 'issue'},
    {'test', 'verify', 'validate', 'check'},
]


def _split_sections(content: str) -> List[Dict]:
    """콘텐츠를 섹션으로 분할합니다."""
    headings = list(_HEADING.finditer(content))

    if not headings:
        return [{'title': '(전체)', 'text': content}]

    sections = []
    for i, m in enumerate(headings):
        start = m.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        sections.append({
            'title': m.group(1).strip()[:40],
            'text': content[start:end],
        })

    return sections


_KO_PARTICLES = re.compile(
    r'(?:이|가|은|는|을|를|에서|에게|에|와|과|의|도|으로|로|만|까지|부터|처럼|보다|이라|라)$'
)


def _strip_particle(word: str) -> str:
    """한국어 조사를 제거합니다."""
    stripped = _KO_PARTICLES.sub('', word)
    return stripped if len(stripped) >= 2 else word


def _extract_terms(text: str) -> Counter:
    """텍스트에서 용어 빈도를 추출합니다."""
    words = _WORD_SPLIT.findall(text)
    processed = []
    for w in words:
        if len(w) < 2:
            continue
        if re.match(r'[가-힣]', w):
            processed.append(_strip_particle(w))
        else:
            processed.append(w.lower())
    return Counter(processed)


def _find_drifts(sections: List[Dict]) -> List[Dict]:
    """섹션 간 동의어 혼용을 찾습니다."""
    if len(sections) < 2:
        return []

    # 각 섹션별 용어 추출
    section_terms = []
    for sec in sections:
        terms = _extract_terms(sec['text'])
        section_terms.append(terms)

    drifts = []
    all_groups = _SYNONYM_GROUPS + _EN_SYNONYM_GROUPS

    for group in all_groups:
        # 이 동의어 그룹에서 사용된 용어 수집
        used_terms = {}  # term -> [section_indices]
        for idx, terms in enumerate(section_terms):
            for term in group:
                if terms.get(term, 0) > 0:
                    if term not in used_terms:
                        used_terms[term] = []
                    used_terms[term].append(idx)

        # 2개 이상의 다른 용어가 사용된 경우 = drift
        if len(used_terms) >= 2:
            terms_list = list(used_terms.keys())
            sections_involved = set()
            for idxs in used_terms.values():
                sections_involved.update(idxs)

            drifts.append({
                'terms': terms_list[:4],
                'concept_group': sorted(group)[:3],
                'sections_count': len(sections_involved),
            })

    return drifts


def analyze_terminology_drift(content: str) -> dict:
    """섹션 간 용어 혼용(드리프트)을 분석합니다.

    Returns:
        score, summary, drift_items, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'total_sections': 0,
                'drift_count': 0,
                'level': 'none',
            },
            'drift_items': [],
            'suggestions': [],
        }

    sections = _split_sections(content)

    if len(sections) < 2:
        return {
            'score': 100.0,
            'summary': {
                'total_sections': len(sections),
                'drift_count': 0,
                'level': 'none',
            },
            'drift_items': [],
            'suggestions': [],
        }

    drifts = _find_drifts(sections)
    drift_count = len(drifts)

    # 레벨 판정
    if drift_count == 0:
        level = 'consistent'
    elif drift_count <= 2:
        level = 'minor'
    elif drift_count <= 5:
        level = 'moderate'
    else:
        level = 'drifting'

    # 점수 계산
    if level == 'consistent':
        score = 100.0
    elif level == 'minor':
        score = 80.0
    elif level == 'moderate':
        score = 55.0
    else:
        score = 30.0

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(drifts, level, len(sections))

    return {
        'score': score,
        'summary': {
            'total_sections': len(sections),
            'drift_count': drift_count,
            'level': level,
        },
        'drift_items': drifts[:10],
        'suggestions': suggestions,
    }


def _generate_suggestions(drifts: List[Dict], level: str,
                           section_count: int) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'consistent': '일관적',
        'minor': '경미', 'moderate': '보통', 'drifting': '혼용',
    }
    suggestions.append(
        f'용어 일관성: {level_labels.get(level, level)}. '
        f'{section_count}개 섹션에서 {len(drifts)}건 동의어 혼용 감지.'
    )

    if drifts:
        suggestions.append(
            '같은 개념에는 문서 전체에서 하나의 용어만 사용하세요.'
        )

    for drift in drifts[:3]:
        terms = ', '.join(drift['terms'][:3])
        suggestions.append(
            f'혼용 감지: {terms} — 하나로 통일하세요.'
        )

    return suggestions
