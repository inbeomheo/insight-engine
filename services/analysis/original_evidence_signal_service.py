"""
Original Evidence Signal Analyzer 서비스

독자적 테스트, 직접 경험, 자체 데이터 등
원본 증거 신호가 콘텐츠에 포함되어 있는지 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List
import logging

logger = logging.getLogger(__name__)

# 직접 경험 패턴
_DIRECT_EXPERIENCE = {
    'label': '직접 경험',
    'patterns': [
        re.compile(r'(?:직접\s*(?:사용|테스트|체험|경험|확인|측정|비교))', re.IGNORECASE),
        re.compile(r'(?:실제로\s*(?:사용|해\s*보|써\s*보|테스트))', re.IGNORECASE),
        re.compile(r'(?:(?:우리|저|필자|제)가?\s*(?:테스트|측정|확인|분석))', re.IGNORECASE),
        re.compile(r'\b(?:I\s+(?:tested|tried|used|measured|benchmarked))\b', re.IGNORECASE),
        re.compile(r'\b(?:we\s+(?:tested|ran|conducted|measured|found))\b', re.IGNORECASE),
        re.compile(r'\b(?:in\s+(?:my|our)\s+(?:experience|testing|analysis))\b', re.IGNORECASE),
    ],
}

# 자체 데이터/결과
_ORIGINAL_DATA = {
    'label': '자체 데이터',
    'patterns': [
        re.compile(r'(?:자체\s*(?:테스트|조사|설문|분석|데이터|결과))', re.IGNORECASE),
        re.compile(r'(?:(?:우리|자사|내부)\s*(?:데이터|분석|조사|통계))', re.IGNORECASE),
        re.compile(r'(?:(?:측정|실험)\s*결과)', re.IGNORECASE),
        re.compile(r'\b(?:our\s+(?:data|results|findings|analysis|survey))\b', re.IGNORECASE),
        re.compile(r'\b(?:(?:internal|proprietary|original)\s+(?:data|research|study))\b', re.IGNORECASE),
    ],
}

# 스크린샷/이미지 증거
_VISUAL_EVIDENCE = {
    'label': '시각적 증거',
    'patterns': [
        re.compile(r'(?:스크린샷|캡처|화면\s*(?:사진|캡처)|아래\s*(?:사진|이미지|그림))', re.IGNORECASE),
        re.compile(r'!\[.*?\]\(.*?\)', re.IGNORECASE),  # 마크다운 이미지
        re.compile(r'<img\s', re.IGNORECASE),
        re.compile(r'\b(?:screenshot|screen\s*cap|as\s+shown\s+(?:below|above|here))\b', re.IGNORECASE),
    ],
}

# 구체적 수치/벤치마크
_SPECIFIC_METRICS = {
    'label': '구체적 수치',
    'patterns': [
        re.compile(r'(?:(?:속도|성능|응답\s*시간).*?\d+\s*(?:ms|초|sec|밀리초))', re.IGNORECASE),
        re.compile(r'(?:\d+\s*(?:회|번|건)\s*(?:테스트|실행|반복))', re.IGNORECASE),
        re.compile(r'(?:(?:평균|최대|최소|중앙값)\s*(?:\d|:))', re.IGNORECASE),
        re.compile(r'\b(?:\d+\s*(?:ms|seconds?|requests?/s|RPS|QPS|TPS))\b', re.IGNORECASE),
        re.compile(r'\b(?:latency|throughput|benchmark)\s*(?:of|:|\s)\s*\d', re.IGNORECASE),
    ],
}

# 비교 테스트 환경
_TEST_ENVIRONMENT = {
    'label': '테스트 환경',
    'patterns': [
        re.compile(r'(?:테스트\s*환경|실험\s*(?:환경|조건)|측정\s*조건)', re.IGNORECASE),
        re.compile(r'(?:(?:OS|운영체제|CPU|RAM|메모리|버전)\s*(?::|은|는))', re.IGNORECASE),
        re.compile(r'\b(?:test\s*(?:environment|setup|conditions?)|(?:hardware|software)\s*(?:specs?|config))\b', re.IGNORECASE),
    ],
}

_ALL_CATEGORIES = {
    'direct_experience': _DIRECT_EXPERIENCE,
    'original_data': _ORIGINAL_DATA,
    'visual_evidence': _VISUAL_EVIDENCE,
    'specific_metrics': _SPECIFIC_METRICS,
    'test_environment': _TEST_ENVIRONMENT,
}


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


def analyze_original_evidence(content: str) -> dict:
    """원본 증거 신호를 분석합니다.

    Returns:
        score, summary, evidence_signals, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return {
                'score': 50.0,
                'summary': {
                    'evidence_categories': 0,
                    'signals_found': [],
                    'level': 'none',
                },
                'evidence_signals': [],
                'suggestions': [],
            }

        found_categories = []
        signals = []

        for cat_name, cat_info in _ALL_CATEGORIES.items():
            if _has_pattern(content, cat_info['patterns']):
                found_categories.append(cat_name)
                signals.append({
                    'category': cat_name,
                    'label': cat_info['label'],
                })

        count = len(found_categories)

        # 레벨 판정
        if count >= 4:
            level = 'strong'
        elif count >= 3:
            level = 'good'
        elif count >= 2:
            level = 'partial'
        elif count >= 1:
            level = 'minimal'
        else:
            level = 'missing'

        # 연속 점수 — 카테고리 충족 비율 기반
        total_categories = len(_ALL_CATEGORIES)
        score = 20.0 + (count / total_categories * 80.0)

        score = round(max(0.0, min(100.0, score)), 1)

        suggestions = _generate_suggestions(found_categories, level)

        return {
            'score': score,
            'summary': {
                'evidence_categories': count,
                'signals_found': found_categories,
                'level': level,
            },
            'evidence_signals': signals,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(found: List[str], level: str) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'strong': '강함',
        'good': '양호', 'partial': '부분적',
        'minimal': '최소', 'missing': '없음',
    }
    suggestions.append(
        f'원본 증거 신호: {level_labels.get(level, level)}. '
        f'{len(found)}개 카테고리 감지.'
    )

    missing = set(_ALL_CATEGORIES.keys()) - set(found)
    labels = {k: v['label'] for k, v in _ALL_CATEGORIES.items()}

    if 'direct_experience' not in found:
        suggestions.append(
            '"직접 사용해 봤습니다" 등 직접 경험을 명시하세요.'
        )

    if 'specific_metrics' not in found:
        suggestions.append(
            '구체적 성능 수치(응답 시간, 처리량 등)를 포함하세요.'
        )

    if 'test_environment' not in found:
        suggestions.append(
            '테스트 환경(OS, 버전, 하드웨어)을 명시하세요.'
        )

    return suggestions
