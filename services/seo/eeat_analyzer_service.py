"""
E-E-A-T Trust Signal Analyzer

콘텐츠의 E-E-A-T(Experience, Expertise, Authoritativeness, Trustworthiness)
신뢰 신호를 규칙 기반으로 점검한다. AI API 호출 없이 동작.
"""
import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# ── Experience (경험) 신호 패턴 ──
_EXPERIENCE_CHECKS = {
    '1인칭 경험 표현': {
        'patterns': [r'제가', r'직접', r'경험해보니', r'사용해보니', r'실제로'],
    },
    '사례/결과 공유': {
        'patterns': [r'결과적으로', r'그\s*결과', r'실험\s*결과'],
    },
    '구체적 기간/시점': {
        'patterns': [r'\d+개월간', r'\d{4}년부터', r'작년에', r'\d+년\s*전', r'\d+일간'],
    },
    '스크린샷/이미지 참조': {
        'patterns': [r'아래\s*사진', r'캡처', r'스크린샷', r'!\[', r'<img'],
    },
}

# ── Expertise (전문성) 신호 패턴 ──
_EXPERTISE_CHECKS = {
    '전문용어 사용': {
        # 3개 이상의 영문 약어/전문어 (2글자+ 대문자 약어 또는 CamelCase)
        'custom': '_check_technical_terms',
    },
    '깊이 있는 설명': {
        # 평균 문장 길이 20자+ & 단락 3개+
        'custom': '_check_depth',
    },
    '방법론/프로세스 설명': {
        'patterns': [r'방법', r'절차', r'단계', r'프로세스'],
    },
    '데이터/통계 인용': {
        # 숫자 + 단위(%, 배, 건, 명 등)
        'patterns': [r'\d+\s*%', r'\d+\s*배', r'\d+\s*건', r'\d+\s*명', r'\d+\s*개'],
    },
}

# ── Authoritativeness (권위) 신호 패턴 ──
_AUTHORITY_CHECKS = {
    '출처 인용': {
        'patterns': [r'에\s*따르면', r'연구에\s*의하면', r'보고서에\s*따르면'],
    },
    '외부 링크/참조': {
        'patterns': [r'https?://', r'www\.'],
    },
    '저자 정보 제공': {
        # author_info 존재 여부로 판단 (커스텀)
        'custom': '_check_author_info',
    },
    '발행 기관/매체 언급': {
        'patterns': [r'구글', r'네이버', r'정부', r'공식', r'Google', r'Naver'],
    },
}

# ── Trustworthiness (신뢰성) 신호 패턴 ──
_TRUST_CHECKS = {
    '날짜/업데이트 정보': {
        'patterns': [r'20\d{2}년', r'최신', r'업데이트'],
    },
    '면책/한계 인정': {
        'patterns': [r'다만', r'한계', r'주의할\s*점', r'참고로'],
    },
    '균형 잡힌 시각': {
        'patterns': [r'반면', r'한편', r'그러나', r'다른\s*의견'],
    },
    '구조화된 형식': {
        # 헤딩 3개+, 목록 2개+ (커스텀)
        'custom': '_check_structure',
    },
}

# ── 등급 매핑 ──
_GRADE_THRESHOLDS = [
    (80, 'A'),
    (65, 'B'),
    (50, 'C'),
    (35, 'D'),
]


def _match_patterns(content: str, patterns: list) -> bool:
    """패턴 목록 중 하나라도 매칭되면 True"""
    for pat in patterns:
        if re.search(pat, content):
            return True
    return False


def _check_technical_terms(content: str, _author_info: str) -> bool:
    """영문 약어/전문어가 3개 이상이면 True"""
    # 2글자 이상 대문자 약어 (API, SEO 등)
    abbrs = set(re.findall(r'\b[A-Z]{2,}\b', content))
    # CamelCase 전문어 (JavaScript, TypeScript 등)
    camel = set(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', content))
    return len(abbrs | camel) >= 3


def _check_depth(content: str, _author_info: str) -> bool:
    """평균 문장 길이 20자+ & 단락 3개+"""
    sentences = [s.strip() for s in re.split(r'[.!?。]\s*', content) if s.strip()]
    if not sentences:
        return False
    avg_len = sum(len(s) for s in sentences) / len(sentences)

    # 빈 줄로 구분된 단락 또는 줄바꿈으로 구분
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
    if len(paragraphs) < 3:
        # 단일 줄바꿈도 단락으로 간주
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]

    return avg_len >= 20 and len(paragraphs) >= 3


def _check_author_info(content: str, author_info: str) -> bool:
    """저자 정보가 제공되었는지 확인"""
    return bool(author_info and author_info.strip())


def _check_structure(content: str, _author_info: str) -> bool:
    """헤딩 3개+, 목록 항목 2개+"""
    # 마크다운 헤딩 (# ~ ###) 또는 HTML 헤딩
    headings = re.findall(r'(?m)^#{1,6}\s+.+|<h[1-6][^>]*>', content)
    # 마크다운 목록 (- 또는 * 또는 숫자.) 또는 HTML 목록
    lists = re.findall(r'(?m)^\s*[-*]\s+.+|^\s*\d+\.\s+.+|<li[^>]*>', content)
    return len(headings) >= 3 and len(lists) >= 2


# 커스텀 체크 함수 맵
_CUSTOM_CHECKS = {
    '_check_technical_terms': _check_technical_terms,
    '_check_depth': _check_depth,
    '_check_author_info': _check_author_info,
    '_check_structure': _check_structure,
}


def _evaluate_dimension(
    content: str,
    author_info: str,
    checks: Dict,
) -> tuple:
    """차원 하나를 평가하여 (점수, 발견 신호, 결핍 신호) 반환"""
    score = 0.0
    found: List[str] = []
    missing: List[str] = []
    per_signal = 25.0

    for signal_name, config in checks.items():
        detected = False

        if 'custom' in config:
            func = _CUSTOM_CHECKS[config['custom']]
            detected = func(content, author_info)
        elif 'patterns' in config:
            detected = _match_patterns(content, config['patterns'])

        if detected:
            score += per_signal
            found.append(signal_name)
        else:
            missing.append(signal_name)

    return min(score, 100.0), found, missing


def _score_to_grade(score: float) -> str:
    """점수를 등급으로 변환"""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return 'F'


def _build_suggestions(
    dimensions: Dict[str, float],
    missing: List[str],
) -> List[str]:
    """결핍 신호를 기반으로 개선 제안 생성"""
    suggestions: List[str] = []

    # 가장 낮은 차원부터 제안
    sorted_dims = sorted(dimensions.items(), key=lambda x: x[1])

    dim_labels = {
        'experience': '경험',
        'expertise': '전문성',
        'authoritativeness': '권위',
        'trustworthiness': '신뢰성',
    }

    for dim_key, dim_score in sorted_dims:
        if dim_score >= 75:
            continue
        label = dim_labels.get(dim_key, dim_key)
        suggestions.append(f'{label} 점수가 {dim_score:.0f}점으로 개선이 필요합니다.')

    # 결핍 신호별 구체적 제안
    _SIGNAL_SUGGESTIONS = {
        '1인칭 경험 표현': '직접 경험한 내용("제가 사용해보니", "실제로" 등)을 추가하세요.',
        '사례/결과 공유': '구체적인 사례나 결과("결과적으로", "그 결과" 등)를 공유하세요.',
        '구체적 기간/시점': '구체적인 기간이나 시점("3개월간", "2024년부터" 등)을 명시하세요.',
        '스크린샷/이미지 참조': '스크린샷이나 이미지를 추가하여 신뢰도를 높이세요.',
        '전문용어 사용': '관련 전문 용어나 약어를 적절히 사용하세요.',
        '깊이 있는 설명': '문장과 단락을 충분히 작성하여 깊이를 더하세요.',
        '방법론/프로세스 설명': '방법, 절차, 단계 등을 구체적으로 설명하세요.',
        '데이터/통계 인용': '구체적인 수치(%, 건, 명 등)를 인용하세요.',
        '출처 인용': '출처를 명시하세요("~에 따르면", "연구에 의하면" 등).',
        '외부 링크/참조': '관련 외부 링크나 참고 자료를 추가하세요.',
        '저자 정보 제공': '저자의 전문 분야, 경력 등 정보를 제공하세요.',
        '발행 기관/매체 언급': '공식 기관이나 신뢰할 수 있는 매체를 언급하세요.',
        '날짜/업데이트 정보': '작성일이나 업데이트 날짜를 명시하세요.',
        '면책/한계 인정': '한계나 주의사항("다만", "주의할 점" 등)을 인정하세요.',
        '균형 잡힌 시각': '다양한 관점("반면", "한편", "그러나" 등)을 제시하세요.',
        '구조화된 형식': '헤딩과 목록을 활용하여 콘텐츠를 구조화하세요.',
    }

    for signal in missing:
        if signal in _SIGNAL_SUGGESTIONS:
            suggestions.append(_SIGNAL_SUGGESTIONS[signal])

    return suggestions


_EMPTY_RESULT = {
    'eeat_score': 0.0,
    'grade': 'F',
    'dimensions': {
        'experience': 0.0,
        'expertise': 0.0,
        'authoritativeness': 0.0,
        'trustworthiness': 0.0,
    },
    'signals_found': [],
    'signals_missing': [],
    'suggestions': ['콘텐츠가 비어 있습니다. 분석할 텍스트를 입력하세요.'],
}


def _evaluate_all_dimensions(content: str, author_info: str) -> tuple:
    """4개 E-E-A-T 차원을 모두 평가합니다.

    Returns:
        (dimensions, all_found, all_missing)
    """
    checks_map = [
        ('experience', _EXPERIENCE_CHECKS),
        ('expertise', _EXPERTISE_CHECKS),
        ('authoritativeness', _AUTHORITY_CHECKS),
        ('trustworthiness', _TRUST_CHECKS),
    ]

    dimensions = {}
    all_found = []
    all_missing = []

    for dim_key, checks in checks_map:
        score, found, missing = _evaluate_dimension(content, author_info, checks)
        dimensions[dim_key] = score
        all_found.extend(found)
        all_missing.extend(missing)

    return dimensions, all_found, all_missing


def analyze_eeat(content: str, author_info: str = '') -> dict:
    """콘텐츠의 E-E-A-T 신뢰 신호를 분석합니다.

    Args:
        content: 분석할 콘텐츠 텍스트
        author_info: 저자 정보 (선택)

    Returns:
        eeat_score, grade, dimensions, signals_found, signals_missing, suggestions
    """
    if not content or not isinstance(content, str) or not content.strip():
        return dict(_EMPTY_RESULT)

    dimensions, all_found, all_missing = _evaluate_all_dimensions(content, author_info)
    eeat_score = sum(dimensions.values()) / 4.0
    grade = _score_to_grade(eeat_score)

    logger.debug(
        'E-E-A-T 분석 완료: score=%.1f, grade=%s, found=%d, missing=%d',
        eeat_score, grade, len(all_found), len(all_missing),
    )

    return {
        'eeat_score': eeat_score,
        'grade': grade,
        'dimensions': dimensions,
        'signals_found': all_found,
        'signals_missing': all_missing,
        'suggestions': _build_suggestions(dimensions, all_missing),
    }
