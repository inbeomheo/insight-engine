"""루브릭 스코어카드 서비스 — 콘텐츠 품질을 규칙 기반으로 채점."""
import re
import uuid
from dataclasses import dataclass, field


@dataclass
class RubricCriterion:
    """루브릭 평가 기준 항목."""
    name: str
    weight: float  # 가중치 (0.0~1.0)
    description: str


@dataclass
class Rubric:
    """평가 루브릭 (기준 항목 집합)."""
    name: str
    criteria: dict = field(default_factory=dict)  # key → RubricCriterion


@dataclass
class ScoreDetail:
    """개별 기준 채점 결과."""
    criterion: str
    score: float      # 0~100
    max_score: float   # 항상 100
    feedback: str


@dataclass
class Scorecard:
    """최종 스코어카드."""
    content_id: str
    scores: dict = field(default_factory=dict)       # criterion → score
    total_score: float = 0.0
    grade: str = 'F'
    details: list = field(default_factory=list)      # list[ScoreDetail]


# 금지 표현 목록 (CLAUDE.md 프롬프트 규칙과 동일)
_FORBIDDEN_WORDS = [
    '놀라운', '혁신적', '획기적', '최고의', '게임체인저',
    '압도적', '경이로운', '드디어', '탁월한', '인상적', '뛰어난', '강력한',
]

# 기본 루브릭 정의
_DEFAULT_CRITERIA = {
    'factuality': RubricCriterion(
        name='사실성',
        weight=0.3,
        description='숫자, 통계, 구체적 데이터 포함 여부',
    ),
    'brand_voice': RubricCriterion(
        name='브랜드 보이스',
        weight=0.2,
        description='금지 표현 미사용 여부',
    ),
    'citation': RubricCriterion(
        name='인용',
        weight=0.2,
        description='출처/참조/링크 언급 여부',
    ),
    'seo': RubricCriterion(
        name='SEO',
        weight=0.3,
        description='키워드 밀도, 제목/소제목 구조',
    ),
}


def _default_rubric() -> Rubric:
    """기본 루브릭을 반환합니다."""
    return Rubric(name='default', criteria=dict(_DEFAULT_CRITERIA))


def _score_factuality(content: str) -> ScoreDetail:
    """사실성 채점 — 숫자/통계/구체적 데이터 포함 여부."""
    if not content or not content.strip():
        return ScoreDetail('factuality', 0.0, 100.0, '콘텐츠가 비어 있습니다.')

    score = 0.0
    feedback_parts = []

    # 숫자/통계 포함 여부 (예: 123, 45%, 3.14)
    numbers = re.findall(r'\d+\.?\d*%?', content)
    if len(numbers) >= 5:
        score += 40.0
        feedback_parts.append(f'숫자/통계 {len(numbers)}개 포함')
    elif len(numbers) >= 2:
        score += 25.0
        feedback_parts.append(f'숫자/통계 {len(numbers)}개 포함')
    elif len(numbers) >= 1:
        score += 10.0
        feedback_parts.append(f'숫자/통계 {len(numbers)}개 포함 (부족)')
    else:
        feedback_parts.append('숫자/통계 없음')

    # 구체적 단위 포함 (%, 원, 달러, GB, MB, 초, 분, 시간 등)
    units = re.findall(r'\d+\s*(원|달러|\$|%|GB|MB|KB|초|분|시간|일|개월|년)', content)
    if len(units) >= 3:
        score += 30.0
        feedback_parts.append(f'단위 표현 {len(units)}개')
    elif len(units) >= 1:
        score += 15.0
        feedback_parts.append(f'단위 표현 {len(units)}개')

    # 비교/대조 표현 ("보다", "대비", "증가", "감소")
    comparisons = re.findall(r'(보다|대비|증가|감소|상승|하락|비해)', content)
    if len(comparisons) >= 2:
        score += 30.0
        feedback_parts.append(f'비교 표현 {len(comparisons)}개')
    elif len(comparisons) >= 1:
        score += 15.0
        feedback_parts.append(f'비교 표현 {len(comparisons)}개')

    score = min(score, 100.0)
    return ScoreDetail('factuality', score, 100.0, '; '.join(feedback_parts))


def _score_brand_voice(content: str) -> ScoreDetail:
    """브랜드 보이스 채점 — 금지 표현 미사용 여부."""
    if not content or not content.strip():
        return ScoreDetail('brand_voice', 100.0, 100.0, '콘텐츠가 비어 있습니다.')

    found = [w for w in _FORBIDDEN_WORDS if w in content]
    if not found:
        return ScoreDetail('brand_voice', 100.0, 100.0, '금지 표현 없음')

    # 금지 표현 1개당 15점 감점
    penalty = min(len(found) * 15, 100)
    score = max(0.0, 100.0 - penalty)
    return ScoreDetail(
        'brand_voice', score, 100.0,
        f'금지 표현 발견: {", ".join(found)}',
    )


def _score_citation(content: str) -> ScoreDetail:
    """인용 채점 — 출처/참조/링크 언급 여부."""
    if not content or not content.strip():
        return ScoreDetail('citation', 0.0, 100.0, '콘텐츠가 비어 있습니다.')

    score = 0.0
    feedback_parts = []

    # URL 링크 ([텍스트](url) 또는 http로 시작하는 URL)
    urls = re.findall(r'https?://[^\s)\]]+', content)
    if len(urls) >= 3:
        score += 40.0
        feedback_parts.append(f'URL {len(urls)}개')
    elif len(urls) >= 1:
        score += 20.0
        feedback_parts.append(f'URL {len(urls)}개')

    # 타임스탬프 인용 [MM:SS]
    timestamps = re.findall(r'\[\d{1,2}:\d{2}\]', content)
    if len(timestamps) >= 3:
        score += 30.0
        feedback_parts.append(f'타임스탬프 인용 {len(timestamps)}개')
    elif len(timestamps) >= 1:
        score += 15.0
        feedback_parts.append(f'타임스탬프 인용 {len(timestamps)}개')

    # 출처/참고 키워드
    ref_keywords = re.findall(r'(출처|참고|참조|인용|근거|원문|자료)', content)
    if len(ref_keywords) >= 2:
        score += 30.0
        feedback_parts.append(f'참조 키워드 {len(ref_keywords)}개')
    elif len(ref_keywords) >= 1:
        score += 15.0
        feedback_parts.append(f'참조 키워드 {len(ref_keywords)}개')

    if not feedback_parts:
        feedback_parts.append('인용/출처 없음')

    score = min(score, 100.0)
    return ScoreDetail('citation', score, 100.0, '; '.join(feedback_parts))


def _score_seo(content: str) -> ScoreDetail:
    """SEO 채점 — 키워드 밀도, 제목/소제목 구조."""
    if not content or not content.strip():
        return ScoreDetail('seo', 0.0, 100.0, '콘텐츠가 비어 있습니다.')

    score = 0.0
    feedback_parts = []

    # 마크다운 제목 구조 (H1, H2, H3)
    headings = re.findall(r'^#{1,3}\s+.+', content, re.MULTILINE)
    if len(headings) >= 4:
        score += 35.0
        feedback_parts.append(f'제목/소제목 {len(headings)}개')
    elif len(headings) >= 2:
        score += 20.0
        feedback_parts.append(f'제목/소제목 {len(headings)}개')
    elif len(headings) >= 1:
        score += 10.0
        feedback_parts.append(f'제목/소제목 {len(headings)}개 (부족)')
    else:
        feedback_parts.append('제목/소제목 없음')

    # 콘텐츠 길이 (SEO 관점에서 충분한 길이)
    char_count = len(content.strip())
    if char_count >= 2000:
        score += 25.0
        feedback_parts.append(f'충분한 길이 ({char_count}자)')
    elif char_count >= 1000:
        score += 15.0
        feedback_parts.append(f'적절한 길이 ({char_count}자)')
    elif char_count >= 500:
        score += 8.0
        feedback_parts.append(f'짧은 길이 ({char_count}자)')
    else:
        feedback_parts.append(f'매우 짧음 ({char_count}자)')

    # 리스트 구조 (순서/비순서 목록)
    lists = re.findall(r'^[\s]*[-*]\s|^\s*\d+\.\s', content, re.MULTILINE)
    if len(lists) >= 3:
        score += 20.0
        feedback_parts.append(f'목록 {len(lists)}개')
    elif len(lists) >= 1:
        score += 10.0
        feedback_parts.append(f'목록 {len(lists)}개')

    # 굵은 글씨/강조 (키워드 강조)
    bolds = re.findall(r'\*\*[^*]+\*\*', content)
    if len(bolds) >= 3:
        score += 20.0
        feedback_parts.append(f'강조 {len(bolds)}개')
    elif len(bolds) >= 1:
        score += 10.0
        feedback_parts.append(f'강조 {len(bolds)}개')

    score = min(score, 100.0)
    return ScoreDetail('seo', score, 100.0, '; '.join(feedback_parts))


# 기준별 채점 함수 매핑
_SCORERS = {
    'factuality': _score_factuality,
    'brand_voice': _score_brand_voice,
    'citation': _score_citation,
    'seo': _score_seo,
}


def _calculate_grade(total_score: float) -> str:
    """총점 기반 등급을 반환합니다."""
    if total_score >= 90:
        return 'A'
    elif total_score >= 80:
        return 'B'
    elif total_score >= 70:
        return 'C'
    elif total_score >= 60:
        return 'D'
    return 'F'


def create_rubric(name: str, criteria: dict) -> Rubric:
    """커스텀 루브릭을 생성합니다.

    Args:
        name: 루브릭 이름
        criteria: {key: {'name': str, 'weight': float, 'description': str}}

    Returns:
        Rubric 인스턴스
    """
    parsed = {}
    for key, spec in criteria.items():
        parsed[key] = RubricCriterion(
            name=spec.get('name', key),
            weight=spec.get('weight', 0.25),
            description=spec.get('description', ''),
        )
    return Rubric(name=name, criteria=parsed)


def score_content(content: str, rubric: Rubric = None) -> Scorecard:
    """콘텐츠를 루브릭 기준으로 채점합니다.

    Args:
        content: 채점할 콘텐츠 문자열
        rubric: 평가 루브릭 (None이면 기본 루브릭 사용)

    Returns:
        Scorecard — 기준별 점수, 총점, 등급, 상세 피드백
    """
    if rubric is None:
        rubric = _default_rubric()

    content_id = str(uuid.uuid4())
    details = []
    scores = {}

    for key, criterion in rubric.criteria.items():
        scorer = _SCORERS.get(key)
        if scorer:
            detail = scorer(content or '')
        else:
            # 지원하지 않는 기준은 0점 처리
            detail = ScoreDetail(key, 0.0, 100.0, '채점 함수 미등록')
        details.append(detail)
        scores[key] = detail.score

    # 가중 평균 계산
    total_weight = sum(c.weight for c in rubric.criteria.values())
    if total_weight > 0:
        total_score = sum(
            scores.get(key, 0.0) * criterion.weight
            for key, criterion in rubric.criteria.items()
        ) / total_weight
    else:
        total_score = 0.0

    total_score = round(total_score, 1)
    grade = _calculate_grade(total_score)

    return Scorecard(
        content_id=content_id,
        scores=scores,
        total_score=total_score,
        grade=grade,
        details=details,
    )
