"""
AI Answer Engine Optimizer (AEO) 서비스

콘텐츠가 AI 검색엔진(ChatGPT, Perplexity, Gemini 등)에서
답변으로 인용될 가능성을 규칙 기반으로 분석하고 최적화를 제안한다.
AI API 호출 없이 순수 규칙 기반.
"""
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# === 패턴 정의 ===

# 정의형 문장 패턴 ("~은/는 ~이다", "~란 ~를 말한다" 등)
_DEFINITION_PATTERNS = [
    re.compile(r'.{2,}(?:은|는|이란|란)\s+.{2,}(?:이다|입니다|를 말한다|를 의미한다|를 뜻한다|다\.)'),
    re.compile(r'.{2,}(?:이란|란)\s+.{2,}(?:것이다|것입니다|개념이다|개념입니다)'),
]

# 질문-답변 패턴
_QA_PATTERNS = [
    re.compile(r'(?:무엇|뭐|어떤 것)'),
    re.compile(r'어떻게'),
    re.compile(r'왜'),
    re.compile(r'언제'),
    re.compile(r'누가|누구'),
]

# 요약/결론 키워드
_SUMMARY_KEYWORDS = ['요약', '결론', '정리', '마무리', '핵심 정리', '한줄 요약']

# 마크다운 헤딩 패턴
_HEADING_PATTERN = re.compile(r'^#{2,6}\s+.+', re.MULTILINE)

# 목록 패턴 (-, *, 1. 등)
_LIST_PATTERN = re.compile(r'^[\s]*(?:[-*]|\d+\.)\s+.+', re.MULTILINE)

# 표 패턴
_TABLE_PATTERN = re.compile(r'\|.+\|')

# 코드 블록 패턴
_CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```')

# 숫자/통계 패턴
_STAT_PATTERNS = [
    re.compile(r'\d+(?:\.\d+)?%'),
    re.compile(r'\d+(?:\.\d+)?배'),
    re.compile(r'\d{1,3}(?:,\d{3})*\s*명'),
    re.compile(r'\d+(?:\.\d+)?(?:만|억|조)'),
]

# 출처 언급 패턴
_SOURCE_PATTERNS = [
    re.compile(r'에 따르면'),
    re.compile(r'연구\s*결과'),
    re.compile(r'보고서'),
    re.compile(r'조사에 의하면'),
    re.compile(r'발표한 바'),
    re.compile(r'통계에 따르면'),
]

# 날짜/시기 패턴
_DATE_PATTERNS = [
    re.compile(r'20\d{2}년'),
    re.compile(r'최근'),
    re.compile(r'올해'),
    re.compile(r'지난해|작년'),
]

# 전문 용어 + 괄호 설명 패턴
_TERM_EXPLANATION_PATTERN = re.compile(r'[가-힣A-Za-z]+\s*\([^)]{2,}\)')

# 접속사 패턴
_CONJUNCTION_PATTERNS = [
    re.compile(r'(?:따라서|그러므로|그래서|때문에|왜냐하면|반면에|한편|또한|그리고|하지만|그러나|즉|다시 말해|예를 들어|특히|결국|결과적으로)')
]

# 독창적 분석 패턴
_ANALYSIS_PATTERNS = [
    re.compile(r'분석\s*결과'),
    re.compile(r'주목할\s*점'),
    re.compile(r'눈여겨\s*볼'),
    re.compile(r'시사점'),
    re.compile(r'의미하는 바'),
]

# 실용적 조언 패턴
_ADVICE_PATTERNS = [
    re.compile(r'하세요'),
    re.compile(r'하면 됩니다'),
    re.compile(r'팁'),
    re.compile(r'추천합니다'),
    re.compile(r'방법은'),
    re.compile(r'해 보세요'),
    re.compile(r'해보세요'),
]

# FAQ / Q&A 패턴
_FAQ_PATTERNS = [
    re.compile(r'(?:FAQ|Q&A|자주\s*묻는\s*질문)', re.IGNORECASE),
    re.compile(r'^(?:Q|질문)\s*[.:]\s*.+', re.MULTILINE),
    re.compile(r'^(?:A|답변|답)\s*[.:]\s*.+', re.MULTILINE),
]

# 의도-구조 매핑 (쿼리 의도 → 콘텐츠 구조 키워드)
_INTENT_STRUCTURE_MAP = {
    '어떻게': ['방법', '단계', '절차', '순서', '1.', '2.', '3.', 'step'],
    '왜': ['이유', '원인', '때문', '배경'],
    '무엇': ['정의', '개념', '이란', '의미'],
    '비교': ['차이', '비교', '반면', '장단점', 'vs'],
    '추천': ['추천', '베스트', '순위', '목록'],
    '장점': ['장점', '단점', '장단점', '이점', '혜택'],
}

# 가중치
_WEIGHTS = {
    'direct_answer': 0.25,
    'structured_data': 0.20,
    'authority_signals': 0.20,
    'clarity': 0.20,
    'citation_worthiness': 0.15,
}

# 등급 기준
_GRADE_THRESHOLDS = [
    (80, 'A'),
    (65, 'B'),
    (50, 'C'),
    (35, 'D'),
]


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리한다."""
    # 마침표/물음표/느낌표 뒤의 공백 또는 줄바꿈으로 분리
    sentences = re.split(r'(?<=[.?!])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _split_paragraphs(text: str) -> list[str]:
    """텍스트를 단락 단위로 분리한다."""
    paragraphs = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def _get_first_paragraph(text: str) -> str:
    """첫 번째 단락을 반환한다. 마크다운 헤딩은 건너뛴다."""
    lines = text.strip().split('\n')
    paragraph_lines = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        if stripped.startswith('#'):
            if started:
                break
            continue
        started = True
        paragraph_lines.append(stripped)
    return ' '.join(paragraph_lines)


def _count_pattern_matches(text: str, patterns: list[re.Pattern]) -> int:
    """패턴 리스트에서 매칭되는 총 횟수를 반환한다."""
    count = 0
    for pattern in patterns:
        count += len(pattern.findall(text))
    return count


def _score_direct_answer(content: str) -> float:
    """직접 답변 제공 여부를 채점한다 (0-100)."""
    score = 0.0

    # 정의형 문장 포함: +30
    for pattern in _DEFINITION_PATTERNS:
        if pattern.search(content):
            score += 30
            break

    # 첫 2문장 내에 핵심 답변 (50자 이내 완결 문장): +25
    sentences = _split_sentences(content)
    first_two = sentences[:2] if len(sentences) >= 2 else sentences
    for sent in first_two:
        # 마크다운 헤딩 제거 후 검사
        clean = re.sub(r'^#+\s*', '', sent).strip()
        if 5 <= len(clean) <= 50 and re.search(r'[.다요]$', clean):
            score += 25
            break

    # 질문-답변 패턴: +25
    if _count_pattern_matches(content, _QA_PATTERNS) >= 1:
        score += 25

    # 요약/결론 섹션 존재: +20
    for keyword in _SUMMARY_KEYWORDS:
        if keyword in content:
            score += 20
            break

    return min(score, 100)


def _score_structured_data(content: str) -> float:
    """구조화된 데이터를 채점한다 (0-100)."""
    score = 0.0

    # 마크다운 헤딩 3개 이상: +25
    headings = _HEADING_PATTERN.findall(content)
    if len(headings) >= 3:
        score += 25

    # 목록 2개 이상: +25
    list_items = _LIST_PATTERN.findall(content)
    if len(list_items) >= 2:
        score += 25

    # 표 포함: +25
    if _TABLE_PATTERN.search(content):
        score += 25

    # 코드 블록 또는 예시 포함: +25
    if _CODE_BLOCK_PATTERN.search(content) or '예시' in content or '예:' in content:
        score += 25

    return min(score, 100)


def _score_authority_signals(content: str) -> float:
    """권위 신호를 채점한다 (0-100)."""
    score = 0.0

    # 구체적 숫자/통계: +25
    if _count_pattern_matches(content, _STAT_PATTERNS) >= 1:
        score += 25

    # 출처 언급: +25
    if _count_pattern_matches(content, _SOURCE_PATTERNS) >= 1:
        score += 25

    # 전문 용어 적절한 사용 (괄호 설명 포함 3개 이상): +25
    term_matches = _TERM_EXPLANATION_PATTERN.findall(content)
    if len(term_matches) >= 3:
        score += 25

    # 날짜/시기 언급: +25
    if _count_pattern_matches(content, _DATE_PATTERNS) >= 1:
        score += 25

    return min(score, 100)


def _score_clarity(content: str) -> float:
    """명확성을 채점한다 (0-100)."""
    score = 0.0

    sentences = _split_sentences(content)
    if not sentences:
        return 0.0

    # 평균 문장 길이 40자 이하: +25
    avg_len = sum(len(s) for s in sentences) / len(sentences)
    if avg_len <= 40:
        score += 25

    # 전문 용어 사용 시 괄호 설명 포함: +25
    term_matches = _TERM_EXPLANATION_PATTERN.findall(content)
    if len(term_matches) >= 1:
        score += 25

    # 단락 평균 3-5문장: +25
    paragraphs = _split_paragraphs(content)
    if paragraphs:
        para_sentence_counts = []
        for para in paragraphs:
            para_sents = _split_sentences(para)
            para_sentence_counts.append(len(para_sents))
        avg_sents = sum(para_sentence_counts) / len(para_sentence_counts)
        if 3 <= avg_sents <= 5:
            score += 25

    # 접속사로 문장 연결: +25
    if _count_pattern_matches(content, _CONJUNCTION_PATTERNS) >= 2:
        score += 25

    return min(score, 100)


def _score_citation_worthiness(content: str) -> float:
    """인용 가치를 채점한다 (0-100)."""
    score = 0.0

    # 독창적 분석/의견: +25
    if _count_pattern_matches(content, _ANALYSIS_PATTERNS) >= 1:
        score += 25

    # 실용적 조언: +25
    if _count_pattern_matches(content, _ADVICE_PATTERNS) >= 1:
        score += 25

    # 최신 정보 (연도 키워드): +25
    if _count_pattern_matches(content, _DATE_PATTERNS) >= 1:
        score += 25

    # FAQ 형식 또는 Q&A 패턴: +25
    if _count_pattern_matches(content, _FAQ_PATTERNS) >= 1:
        score += 25

    return min(score, 100)


def _compute_query_alignment(content: str, target_query: str) -> float:
    """쿼리와 콘텐츠의 정합성을 채점한다 (0-100)."""
    if not target_query.strip():
        return 0.0

    score = 0.0
    query_keywords = [kw for kw in target_query.strip().split() if len(kw) >= 2]
    if not query_keywords:
        return 0.0

    first_paragraph = _get_first_paragraph(content)
    # 첫 줄(제목)도 포함
    first_line = content.strip().split('\n')[0] if content.strip() else ''

    # 쿼리 키워드가 제목/첫 단락에 포함: +40
    header_text = first_line + ' ' + first_paragraph
    matched_in_header = sum(1 for kw in query_keywords if kw in header_text)
    if matched_in_header > 0:
        score += 40

    # 쿼리 키워드가 본문 전체에 3회+ 등장: +30
    total_occurrences = sum(content.count(kw) for kw in query_keywords)
    if total_occurrences >= 3:
        score += 30

    # 쿼리 의도와 콘텐츠 구조 매칭: +30
    for intent_keyword, structure_keywords in _INTENT_STRUCTURE_MAP.items():
        if intent_keyword in target_query:
            for sk in structure_keywords:
                if sk in content:
                    score += 30
                    break
            break

    return min(score, 100)


def _generate_optimizations(factors: dict) -> list[dict]:
    """50점 미만인 factor에 대해 최적화 제안을 생성한다."""
    optimizations = []

    optimization_map = {
        'direct_answer': {
            'issue': '콘텐츠에 직접적인 답변이 부족합니다.',
            'fix': '첫 2문장 내에 핵심 답변을 50자 이내로 명확하게 제시하고, '
                   '"~은/는 ~이다" 형식의 정의형 문장을 포함하세요.',
            'impact': 'high',
        },
        'structured_data': {
            'issue': '콘텐츠 구조화가 부족합니다.',
            'fix': '마크다운 헤딩(##, ###)을 3개 이상 사용하고, '
                   '목록(-, 1.)이나 표(|)를 활용하여 정보를 구조화하세요.',
            'impact': 'high',
        },
        'authority_signals': {
            'issue': '콘텐츠의 권위 신호가 부족합니다.',
            'fix': '구체적인 숫자/통계(%, 명)를 포함하고, '
                   '"~에 따르면", "연구 결과" 등 출처를 명시하세요.',
            'impact': 'medium',
        },
        'clarity': {
            'issue': '콘텐츠의 명확성이 부족합니다.',
            'fix': '문장 길이를 40자 이하로 줄이고, 전문 용어에는 괄호 설명을 달아주세요. '
                   '접속사를 활용하여 논리적 흐름을 강화하세요.',
            'impact': 'medium',
        },
        'citation_worthiness': {
            'issue': '인용 가치가 부족합니다.',
            'fix': '독창적 분석("분석 결과", "주목할 점")을 추가하고, '
                   '"~하세요" 형식의 실용적 조언을 포함하세요. '
                   'FAQ 형식도 효과적입니다.',
            'impact': 'low',
        },
    }

    for factor_name, factor_score in factors.items():
        if factor_score < 50 and factor_name in optimization_map:
            opt = optimization_map[factor_name]
            optimizations.append({
                'category': factor_name,
                'issue': opt['issue'],
                'fix': opt['fix'],
                'impact': opt['impact'],
            })

    return optimizations


def _compute_grade(score: float) -> str:
    """점수에 따른 등급을 반환한다."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return 'F'


def _generate_summary(score: float, grade: str, factors: dict) -> str:
    """종합 평가 요약을 생성한다."""
    # 가장 높은/낮은 factor 찾기
    best_factor = max(factors, key=factors.get)
    worst_factor = min(factors, key=factors.get)

    factor_labels = {
        'direct_answer': '직접 답변',
        'structured_data': '구조화',
        'authority_signals': '권위 신호',
        'clarity': '명확성',
        'citation_worthiness': '인용 가치',
    }

    summary = f"AEO 점수 {score:.0f}점({grade}등급)입니다. "
    summary += f"{factor_labels.get(best_factor, best_factor)} 항목이 가장 우수하며, "
    summary += f"{factor_labels.get(worst_factor, worst_factor)} 항목의 개선이 필요합니다."

    return summary


def _generate_suggestions(factors: dict) -> list[str]:
    """개선 제안 리스트를 생성한다."""
    suggestions = []

    if factors['direct_answer'] < 50:
        suggestions.append('콘텐츠 첫 문단에 핵심 답변을 명확히 제시하세요.')
    if factors['structured_data'] < 50:
        suggestions.append('마크다운 헤딩, 목록, 표를 활용하여 구조를 개선하세요.')
    if factors['authority_signals'] < 50:
        suggestions.append('통계 데이터와 출처를 추가하여 신뢰도를 높이세요.')
    if factors['clarity'] < 50:
        suggestions.append('문장을 짧게 쪼개고 전문 용어에 설명을 추가하세요.')
    if factors['citation_worthiness'] < 50:
        suggestions.append('독창적 분석과 실용적 조언을 포함하여 인용 가치를 높이세요.')

    if not suggestions:
        suggestions.append('전반적으로 AEO 최적화가 잘 되어 있습니다. 현재 수준을 유지하세요.')

    return suggestions


def analyze_aeo(content: str, target_query: str = '') -> dict:
    """
    콘텐츠의 AEO(AI Answer Engine Optimization) 점수를 분석한다.

    Args:
        content: 분석할 콘텐츠 텍스트
        target_query: 타겟 검색 쿼리 (선택)

    Returns:
        AEO 분석 결과 dict (aeo_score, grade, factors, optimizations 등)
    """
    # 빈 콘텐츠 / None 처리
    if not content or not content.strip():
        return {
            'aeo_score': 0.0,
            'grade': 'F',
            'factors': {
                'direct_answer': 0.0,
                'structured_data': 0.0,
                'authority_signals': 0.0,
                'clarity': 0.0,
                'citation_worthiness': 0.0,
            },
            'optimizations': _generate_optimizations({
                'direct_answer': 0.0,
                'structured_data': 0.0,
                'authority_signals': 0.0,
                'clarity': 0.0,
                'citation_worthiness': 0.0,
            }),
            'query_alignment': None,
            'summary': 'AEO 점수 0점(F등급)입니다. 콘텐츠가 비어 있어 분석할 수 없습니다.',
            'suggestions': ['콘텐츠를 작성한 후 다시 분석하세요.'],
        }

    # 각 factor 채점
    factors = {
        'direct_answer': _score_direct_answer(content),
        'structured_data': _score_structured_data(content),
        'authority_signals': _score_authority_signals(content),
        'clarity': _score_clarity(content),
        'citation_worthiness': _score_citation_worthiness(content),
    }

    # 가중 평균 계산
    aeo_score = sum(
        factors[k] * _WEIGHTS[k] for k in _WEIGHTS
    )

    # 등급 결정
    grade = _compute_grade(aeo_score)

    # 쿼리 정합성
    query_alignment: Optional[float] = None
    if target_query and target_query.strip():
        query_alignment = _compute_query_alignment(content, target_query)

    # 최적화 제안
    optimizations = _generate_optimizations(factors)

    # 요약
    summary = _generate_summary(aeo_score, grade, factors)

    # 개선 제안
    suggestions = _generate_suggestions(factors)

    result = {
        'aeo_score': round(aeo_score, 1),
        'grade': grade,
        'factors': {k: round(v, 1) for k, v in factors.items()},
        'optimizations': optimizations,
        'query_alignment': round(query_alignment, 1) if query_alignment is not None else None,
        'summary': summary,
        'suggestions': suggestions,
    }

    logger.info(f"AEO 분석 완료: {aeo_score:.1f}점 ({grade}등급)")
    return result
