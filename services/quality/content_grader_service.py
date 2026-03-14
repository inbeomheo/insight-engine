"""
콘텐츠 종합 등급 평가 서비스

readability_service + quality_service를 통합하여
A~F 등급의 종합 콘텐츠 품질 리포트를 생성합니다.

평가 항목:
- 가독성 (readability_service)
- SEO / 구조 / 독창성 (quality_service)
- 참여도 예측 (engagement)
"""
import re
import logging

logger = logging.getLogger(__name__)

_EMPTY_SCORES = {
    'readability': 0, 'seo': 0, 'structure': 0,
    'originality': 0, 'engagement': 0,
}

_WEIGHTS = {
    'readability': 0.20, 'seo': 0.25, 'structure': 0.15,
    'originality': 0.20, 'engagement': 0.20,
}


def _compute_total_score(scores: dict) -> int:
    """가중 평균으로 종합 점수를 계산합니다."""
    total = round(sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS))
    return max(0, min(100, total))


def grade_content(content: str) -> dict:
    """콘텐츠를 종합 평가하여 A~F 등급을 부여합니다.

    Args:
        content: 평가할 콘텐츠 텍스트 (마크다운 가능)

    Returns:
        {
            "grade": str ("A"~"F"),
            "total_score": int (0~100),
            "scores": {
                "readability": int,
                "seo": int,
                "structure": int,
                "originality": int,
                "engagement": int,
            },
            "suggestions": list[str],
            "summary": str,
        }
    """
    if not content or not content.strip():
        return {
            'grade': 'F', 'total_score': 0, 'scores': dict(_EMPTY_SCORES),
            'suggestions': ['콘텐츠가 비어 있습니다.'],
            'summary': '평가할 수 없습니다.',
        }

    from services.analysis.readability_service import analyze_readability
    from services.quality.quality_service import calculate_comprehensive_score

    readability_result = analyze_readability(content)
    quality_result = calculate_comprehensive_score(content)

    scores = {
        'readability': readability_result.get('score', 0),
        'seo': quality_result.get('seo', 0),
        'structure': quality_result.get('structure', 0),
        'originality': quality_result.get('originality', 0),
        'engagement': _predict_engagement(content),
    }
    total = _compute_total_score(scores)
    grade = _score_to_grade(total)

    return {
        'grade': grade, 'total_score': total, 'scores': scores,
        'suggestions': _collect_suggestions(
            readability_result, quality_result, scores['engagement'], content
        ),
        'summary': _generate_summary(grade, total),
    }


def _score_to_grade(score: int) -> str:
    if score >= 90:
        return 'A'
    elif score >= 75:
        return 'B'
    elif score >= 60:
        return 'C'
    elif score >= 40:
        return 'D'
    else:
        return 'F'


def _predict_engagement(content: str) -> int:
    """규칙 기반 참여도 예측 (0~100)."""
    score = 50
    text = content.strip()

    # 질문 포함 (독자 참여 유도)
    questions = re.findall(r'[?？]', text)
    if questions:
        score += min(15, len(questions) * 3)

    # CTA (Call-to-Action) 패턴
    cta_patterns = [
        r'댓글', r'공유', r'구독', r'좋아요', r'알려주세요',
        r'의견', r'경험', r'시도해', r'확인해',
    ]
    cta_count = sum(1 for p in cta_patterns if re.search(p, text))
    score += min(10, cta_count * 3)

    # 구체적 수치/데이터 (신뢰성)
    numbers = re.findall(r'\d+[%만억원달러]', text)
    score += min(10, len(numbers) * 2)

    # 이모지/특수문자 (시각적 관심)
    emoji_count = len(re.findall(r'[^\w\s,.!?;:\'\"()\-\[\]{}#*/\\@&=+<>~`|^$\n\r\t]', text))
    if 1 <= emoji_count <= 10:
        score += 5

    # 글자수 적정 범위 (1000~3000자)
    char_count = len(text)
    if 1000 <= char_count <= 3000:
        score += 10
    elif 500 <= char_count < 1000 or 3000 < char_count <= 5000:
        score += 5

    return max(0, min(100, score))


def _collect_suggestions(
    readability_result: dict,
    quality_result: dict,
    engagement_score: int,
    content: str,
) -> list:
    suggestions = []

    # 가독성 제안
    for s in readability_result.get('suggestions', []):
        if s != '가독성이 양호합니다.':
            suggestions.append(f'[가독성] {s}')

    # SEO 제안
    seo = quality_result.get('seo', 0)
    if seo < 60:
        details = quality_result.get('details', {})
        if details.get('heading_count', 0) < 2:
            suggestions.append('[SEO] 소제목(H2, H3)을 추가하면 검색 노출이 향상됩니다.')
        if details.get('char_count', 0) < 500:
            suggestions.append('[SEO] 콘텐츠 길이가 짧습니다. 500자 이상 작성을 권장합니다.')

    # 구조 제안
    if quality_result.get('structure', 0) < 50:
        suggestions.append('[구조] 서론-본론-결론 구조로 정리하면 가독성이 향상됩니다.')

    # 참여도 제안
    if engagement_score < 50:
        if '?' not in content and '？' not in content:
            suggestions.append('[참여도] 독자에게 질문을 던져 참여를 유도해보세요.')
        suggestions.append('[참여도] 구체적 수치나 사례를 추가하면 신뢰성이 높아집니다.')

    if not suggestions:
        suggestions.append('전반적으로 우수한 콘텐츠입니다.')

    return suggestions


def _generate_summary(grade: str, total: int) -> str:
    summaries = {
        'A': f'우수한 품질의 콘텐츠입니다 ({total}점). 발행에 적합합니다.',
        'B': f'양호한 콘텐츠입니다 ({total}점). 소폭 개선하면 더 좋아집니다.',
        'C': f'보통 수준입니다 ({total}점). 제안 사항을 반영하면 품질이 향상됩니다.',
        'D': f'개선이 필요합니다 ({total}점). 주요 제안 사항을 확인하세요.',
        'F': f'대폭 개선이 필요합니다 ({total}점). 콘텐츠를 재작성하는 것을 권장합니다.',
    }
    return summaries.get(grade, f'평가 완료 ({total}점).')
