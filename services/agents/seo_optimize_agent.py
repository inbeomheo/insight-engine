"""
SEO 자동 최적화 에이전트 — 키워드 밀도, H2/H3 구조, 내부링크 추천

기존 seo_agent.py(파이프라인용 메타데이터 생성)와 달리,
이미 생성된 콘텐츠의 SEO 품질을 분석하고 개선 제안을 반환합니다.
"""
import logging
import re

logger = logging.getLogger(__name__)


def optimize_seo(content: str, keywords: list = None) -> dict:
    """콘텐츠의 SEO를 분석하고 최적화 제안을 반환합니다.

    Args:
        content: 마크다운 콘텐츠
        keywords: 타겟 키워드 목록 (없으면 자동 추출)

    Returns:
        {
            "score": int (0-100),
            "keyword_density": dict,
            "heading_structure": dict,
            "suggestions": list[str],
            "meta_length": dict,
        }
    """
    if not content or not content.strip():
        return {
            'score': 0,
            'keyword_density': {},
            'heading_structure': {'h2': 0, 'h3': 0},
            'suggestions': ['콘텐츠가 비어 있습니다.'],
            'meta_length': {'char_count': 0, 'word_count': 0},
        }

    # 텍스트 전처리 (마크다운 제거)
    plain = _strip_markdown(content)
    char_count = len(plain)
    word_count = len(plain.split())

    # 제목 구조 분석
    headings = _analyze_headings(content)

    # 키워드 밀도 분석
    density = _analyze_keyword_density(plain, keywords or [])

    # SEO 점수 계산 + 제안 생성
    score, suggestions = _evaluate_seo(
        char_count=char_count,
        word_count=word_count,
        headings=headings,
        density=density,
        keywords=keywords or [],
    )

    return {
        'score': score,
        'keyword_density': density,
        'heading_structure': headings,
        'suggestions': suggestions,
        'meta_length': {'char_count': char_count, 'word_count': word_count},
    }


def _strip_markdown(text: str) -> str:
    """마크다운 문법을 제거하고 순수 텍스트만 반환합니다."""
    text = re.sub(r'#{1,6}\s+', '', text)  # 헤딩
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # 볼드
    text = re.sub(r'\*(.+?)\*', r'\1', text)  # 이탤릭
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # 링크
    text = re.sub(r'!\[.*?\]\(.+?\)', '', text)  # 이미지
    text = re.sub(r'```[\s\S]*?```', '', text)  # 코드블록
    text = re.sub(r'`(.+?)`', r'\1', text)  # 인라인 코드
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)  # 리스트
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # 번호 리스트
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)  # 인용
    return text.strip()


def _analyze_headings(content: str) -> dict:
    """마크다운 헤딩 구조를 분석합니다."""
    h2_count = len(re.findall(r'^##\s+', content, re.MULTILINE))
    h3_count = len(re.findall(r'^###\s+', content, re.MULTILINE))
    h2_texts = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
    return {
        'h2': h2_count,
        'h3': h3_count,
        'h2_texts': h2_texts[:10],
    }


def _analyze_keyword_density(text: str, keywords: list) -> dict:
    """키워드 밀도를 분석합니다."""
    if not text:
        return {}

    total_chars = len(text)
    result = {}

    for kw in keywords:
        if not kw:
            continue
        count = text.lower().count(kw.lower())
        density = round((count * len(kw)) / total_chars * 100, 2) if total_chars > 0 else 0
        result[kw] = {
            'count': count,
            'density_percent': density,
        }

    return result


def _evaluate_seo(
    char_count: int,
    word_count: int,
    headings: dict,
    density: dict,
    keywords: list,
) -> tuple:
    """SEO 점수와 제안을 생성합니다."""
    score = 50  # 기본 점수
    suggestions = []

    # 1) 글 길이 (300자 미만이면 SEO 불리)
    if char_count < 300:
        score -= 15
        suggestions.append('글이 너무 짧습니다 (300자 미만). SEO에 불리합니다.')
    elif char_count >= 1000:
        score += 10
    elif char_count >= 500:
        score += 5

    # 2) 헤딩 구조
    h2 = headings.get('h2', 0)
    h3 = headings.get('h3', 0)
    if h2 == 0:
        score -= 10
        suggestions.append('H2 제목이 없습니다. 섹션 구분을 추가하세요.')
    elif h2 >= 2:
        score += 10
    else:
        score += 5

    if h2 > 0 and h3 == 0 and char_count > 1000:
        suggestions.append('긴 글에 H3 소제목을 추가하면 가독성이 향상됩니다.')

    # 3) 키워드 밀도
    if keywords and density:
        avg_density = sum(d['density_percent'] for d in density.values()) / len(density)
        if avg_density < 0.5:
            score -= 5
            suggestions.append('키워드 밀도가 낮습니다 (0.5% 미만). 자연스럽게 키워드를 추가하세요.')
        elif avg_density > 3.0:
            score -= 5
            suggestions.append('키워드 밀도가 높습니다 (3% 초과). 키워드 스터핑 주의.')
        else:
            score += 10

        for kw, info in density.items():
            if info['count'] == 0:
                suggestions.append(f'키워드 "{kw}"가 본문에 없습니다.')
    elif not keywords:
        suggestions.append('타겟 키워드를 설정하면 더 정확한 분석이 가능합니다.')

    # 점수 클램핑
    score = max(0, min(100, score))

    if not suggestions:
        suggestions.append('SEO 구조가 양호합니다.')

    return score, suggestions
