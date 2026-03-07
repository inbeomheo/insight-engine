"""
콘텐츠 가독성 벤치마크 서비스

콘텐츠의 가독성을 업계 기준과 비교하여 상대적 위치를 알려줍니다.
블로그, 뉴스, 학술, 마케팅 등 카테고리별 기준치 제공.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 카테고리별 벤치마크 (평균 문장 길이, 어휘 다양성, 외래어 비율)
_BENCHMARKS = {
    'blog': {
        'label': '블로그',
        'avg_sentence_length': (20, 35),
        'vocabulary_diversity': (0.35, 0.65),
        'foreign_ratio': (0.05, 0.20),
        'ideal_grade': 'B',
    },
    'news': {
        'label': '뉴스',
        'avg_sentence_length': (25, 45),
        'vocabulary_diversity': (0.40, 0.70),
        'foreign_ratio': (0.03, 0.15),
        'ideal_grade': 'A',
    },
    'academic': {
        'label': '학술/기술',
        'avg_sentence_length': (30, 60),
        'vocabulary_diversity': (0.50, 0.80),
        'foreign_ratio': (0.10, 0.35),
        'ideal_grade': 'B',
    },
    'marketing': {
        'label': '마케팅',
        'avg_sentence_length': (15, 30),
        'vocabulary_diversity': (0.30, 0.55),
        'foreign_ratio': (0.05, 0.25),
        'ideal_grade': 'A',
    },
    'sns': {
        'label': 'SNS/소셜',
        'avg_sentence_length': (10, 25),
        'vocabulary_diversity': (0.25, 0.50),
        'foreign_ratio': (0.05, 0.30),
        'ideal_grade': 'B',
    },
}


def benchmark_readability(content: str, category: str = 'blog') -> dict:
    """콘텐츠 가독성을 카테고리 벤치마크와 비교합니다.

    Args:
        content: 분석할 콘텐츠
        category: 비교 기준 카테고리 (blog, news, academic, marketing, sns)

    Returns:
        {
            "category": str,
            "metrics": {
                "avg_sentence_length": float,
                "vocabulary_diversity": float,
                "foreign_ratio": float,
            },
            "benchmarks": {
                "avg_sentence_length": {"value": float, "range": tuple, "status": str},
                ...
            },
            "overall_status": "above" | "within" | "below",
            "percentile": int (0~100),
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'category': category,
            'metrics': {},
            'benchmarks': {},
            'overall_status': 'below',
            'percentile': 0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    if category not in _BENCHMARKS:
        category = 'blog'

    bench = _BENCHMARKS[category]
    metrics = _calculate_metrics(content)

    # 벤치마크 비교
    comparisons = {}
    statuses = []

    for key in ('avg_sentence_length', 'vocabulary_diversity', 'foreign_ratio'):
        value = metrics[key]
        low, high = bench[key]
        if value < low:
            status = 'below'
        elif value > high:
            status = 'above'
        else:
            status = 'within'

        comparisons[key] = {
            'value': value,
            'range': [low, high],
            'status': status,
        }
        statuses.append(status)

    # 종합 상태
    within_count = statuses.count('within')
    if within_count >= 2:
        overall = 'within'
    elif statuses.count('below') >= 2:
        overall = 'below'
    else:
        overall = 'above'

    # 백분위 추정
    percentile = _estimate_percentile(metrics, bench)

    # 제안
    suggestions = _generate_suggestions(comparisons, bench, category)

    return {
        'category': category,
        'category_label': bench['label'],
        'metrics': metrics,
        'benchmarks': comparisons,
        'overall_status': overall,
        'percentile': percentile,
        'suggestions': suggestions,
    }


def get_categories() -> list:
    """사용 가능한 벤치마크 카테고리 목록을 반환합니다."""
    return [
        {'id': k, 'label': v['label']}
        for k, v in _BENCHMARKS.items()
    ]


def _calculate_metrics(content: str) -> dict:
    """콘텐츠 가독성 지표를 계산합니다."""
    plain = re.sub(r'#{1,6}\s+', '', content)
    plain = re.sub(r'\*\*(.+?)\*\*', r'\1', plain)
    plain = re.sub(r'```[\s\S]*?```', '', plain)

    sentences = [s.strip() for s in re.split(r'[.!?。]\s*|\n+', plain) if len(s.strip()) >= 5]
    words = plain.split()
    char_count = len(plain)

    sentence_count = max(len(sentences), 1)
    avg_sentence_length = round(sum(len(s) for s in sentences) / sentence_count, 1)

    unique_words = set(words)
    vocabulary_diversity = round(len(unique_words) / max(len(words), 1), 3)

    english_count = sum(len(m) for m in re.findall(r'[a-zA-Z]{2,}', plain))
    foreign_ratio = round(english_count / max(char_count, 1), 3)

    return {
        'avg_sentence_length': avg_sentence_length,
        'vocabulary_diversity': vocabulary_diversity,
        'foreign_ratio': foreign_ratio,
    }


def _estimate_percentile(metrics: dict, bench: dict) -> int:
    """벤치마크 대비 백분위를 추정합니다."""
    scores = []
    for key in ('avg_sentence_length', 'vocabulary_diversity', 'foreign_ratio'):
        value = metrics[key]
        low, high = bench[key]
        mid = (low + high) / 2
        spread = (high - low) / 2 if high != low else 1

        # 중앙값과의 거리로 점수 계산
        distance = abs(value - mid) / spread
        if distance <= 1:
            scores.append(80 - int(distance * 30))
        else:
            scores.append(max(10, 50 - int(distance * 20)))

    return max(0, min(100, round(sum(scores) / len(scores))))


def _generate_suggestions(comparisons: dict, bench: dict, category: str) -> list:
    suggestions = []

    asl = comparisons['avg_sentence_length']
    if asl['status'] == 'above':
        suggestions.append(
            f"[문장 길이] {bench['label']} 기준보다 문장이 깁니다. "
            f"{asl['range'][0]}~{asl['range'][1]}자 범위로 줄여보세요."
        )
    elif asl['status'] == 'below':
        suggestions.append(
            f"[문장 길이] {bench['label']} 기준보다 문장이 짧습니다. "
            f"내용을 보충하면 좋겠습니다."
        )

    vd = comparisons['vocabulary_diversity']
    if vd['status'] == 'below':
        suggestions.append('[어휘 다양성] 어휘 반복이 많습니다. 동의어를 활용해보세요.')

    fr = comparisons['foreign_ratio']
    if fr['status'] == 'above':
        suggestions.append(f'[외래어 비율] {bench["label"]} 기준보다 외래어가 많습니다. 한국어 표현으로 대체를 검토하세요.')

    if not suggestions:
        suggestions.append(f'{bench["label"]} 카테고리 기준에 잘 부합하는 콘텐츠입니다.')

    return suggestions
