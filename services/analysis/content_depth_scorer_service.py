"""
Content Depth Scorer 서비스

콘텐츠의 심도를 예시, 근거, 설명, 비교 등
다양한 지표로 측정하여 얕은 콘텐츠를 개선합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# ── 심도 지표 패턴 ──
# 1. 예시/사례
_EXAMPLE_PATTERNS = [
    re.compile(r'(?:예를\s*들어|예시|사례|예컨대|가령)', re.IGNORECASE),
    re.compile(r'\b(?:for\s+example|for\s+instance|e\.g\.|such\s+as)\b', re.IGNORECASE),
]

# 2. 근거/데이터
_EVIDENCE_PATTERNS = [
    re.compile(r'(?:연구|조사|통계|데이터|실험|결과)'),
    re.compile(r'\b(?:research|study|data|survey|experiment|evidence)\b', re.IGNORECASE),
    re.compile(r'\d+(?:\.\d+)?%'),                     # 퍼센트
    re.compile(r'(?:만|억|천)\s*(?:원|명|건|개)'),       # 한국어 수량
    re.compile(r'\$[\d,]+|\d+\s*(?:million|billion)\b', re.IGNORECASE),
]

# 3. 비교/대조
_COMPARISON_PATTERNS = [
    re.compile(r'(?:반면|비교|대조|차이|구별)'),
    re.compile(r'\b(?:compared\s+to|in\s+contrast|whereas|unlike|differ)\b', re.IGNORECASE),
    re.compile(r'\b(?:vs\.?|versus)\b', re.IGNORECASE),
]

# 4. 인과 관계
_CAUSAL_PATTERNS = [
    re.compile(r'(?:때문에|따라서|그래서|결과적으로|원인|이유)'),
    re.compile(r'\b(?:because|therefore|consequently|as\s+a\s+result|due\s+to)\b', re.IGNORECASE),
]

# 5. 전문 용어/정의
_DEFINITION_PATTERNS = [
    re.compile(r'(?:정의|의미|뜻|개념)(?:는|은|가|이)'),
    re.compile(r'\b(?:defined\s+as|refers\s+to|meaning|in\s+other\s+words)\b', re.IGNORECASE),
]

# 6. 코드/실습
_CODE_PATTERN = re.compile(r'```', re.MULTILINE)
_INLINE_CODE = re.compile(r'`[^`]+`')


def _count_patterns(content: str, patterns: list) -> int:
    count = 0
    for p in patterns:
        count += len(p.findall(content))
    return count


_EMPTY_RESULT = {
    'depth_indicators': {},
    'summary': {'total_indicators': 0, 'depth_level': 'empty',
                'word_count': 0, 'indicator_density': 0.0},
    'score': 0.0,
    'suggestions': [],
}


def _measure_depth_indicators(content: str) -> dict:
    """콘텐츠에서 심도 지표를 측정합니다."""
    return {
        'examples': _count_patterns(content, _EXAMPLE_PATTERNS),
        'evidence': _count_patterns(content, _EVIDENCE_PATTERNS),
        'comparisons': _count_patterns(content, _COMPARISON_PATTERNS),
        'causal_reasoning': _count_patterns(content, _CAUSAL_PATTERNS),
        'definitions': _count_patterns(content, _DEFINITION_PATTERNS),
        'code_blocks': len(_CODE_PATTERN.findall(content)) // 2,
        'inline_code': len(_INLINE_CODE.findall(content)),
    }


def _compute_depth_score(indicators: dict, word_count: int) -> tuple:
    """심도 점수와 레벨을 계산합니다.

    Returns:
        (score, depth_level, density)
    """
    total_indicators = sum(indicators.values())
    density = round((total_indicators / word_count * 100) if word_count > 0 else 0.0, 2)

    active = sum(1 for v in indicators.values() if v > 0)
    score = round(max(0.0, min(100.0, min(60.0, density * 15.0) + (active / 7) * 40.0)), 1)

    if score >= 80:
        level = 'deep'
    elif score >= 50:
        level = 'moderate'
    elif score >= 20:
        level = 'shallow'
    else:
        level = 'surface'

    return score, level, density


def score_content_depth(content: str) -> dict:
    """콘텐츠 심도를 측정합니다.

    Returns:
        depth_indicators, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        indicators = _measure_depth_indicators(content)
        word_count = len(re.findall(r'[A-Za-z]+', content)) + len(re.findall(r'[가-힣]+', content))
        score, depth_level, density = _compute_depth_score(indicators, word_count)

        return {
            'depth_indicators': indicators,
            'summary': {'total_indicators': sum(indicators.values()), 'depth_level': depth_level,
                         'word_count': word_count, 'indicator_density': density},
            'score': score,
            'suggestions': _generate_suggestions(
                indicators, depth_level, sum(1 for v in indicators.values() if v > 0), density
            ),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(indicators: Dict, level: str, active: int, density: float) -> List[str]:
    suggestions = []

    level_labels = {
        'deep': '깊이 있는 콘텐츠',
        'moderate': '보통 수준의 심도',
        'shallow': '얕은 콘텐츠',
        'surface': '표면적 콘텐츠',
    }
    suggestions.append(f'콘텐츠 심도: {level_labels.get(level, level)}.')

    missing = []
    if indicators['examples'] == 0:
        missing.append('예시/사례')
    if indicators['evidence'] == 0:
        missing.append('근거/데이터')
    if indicators['comparisons'] == 0:
        missing.append('비교/대조')
    if indicators['causal_reasoning'] == 0:
        missing.append('인과 관계')

    if missing:
        names = ', '.join(missing[:3])
        suggestions.append(f'부족한 심도 지표: {names}. 해당 요소를 추가하면 콘텐츠 깊이가 향상됩니다.')

    return suggestions
