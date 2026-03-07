"""
Promise Match Auditor 서비스

제목/소제목이 약속한 핵심 키워드가 본문에서
실제로 다뤄지는지 검증합니다.
AI API 호출 없이 순수 Python(re, collections)으로 동작합니다.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# 한국어 불용어 (조사, 어미, 관형사 등)
_STOPWORDS = {
    '은', '는', '이', '가', '을', '를', '의', '에', '와', '과',
    '도', '로', '으로', '에서', '까지', '부터', '만', '라', '며',
    '및', '등', '위한', '대한', '통한', '위해', '통해', '그리고',
    '하는', '있는', '되는', '된', '한', '할', '그', '이런', '저런',
    '어떤', '모든', '각', '다른', '새로운', '좋은', '많은',
}

# 조사 제거 패턴
_PARTICLES = re.compile(
    r'(은|는|이|가|을|를|의|에|와|과|도|로|으로|에서|까지|부터|만|라|며|들|에게|한테|께)$'
)


def audit_promise_match(content: str) -> dict:
    """제목/소제목의 약속 키워드가 본문에서 이행되는지 검증합니다.

    Args:
        content: 분석할 마크다운/텍스트 콘텐츠

    Returns:
        {
            "promises": [{"keyword", "source", "found_in_body", "frequency",
                          "in_intro", "in_conclusion", "status"}],
            "fulfillment_score": float,  # 0-100
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'promises': [],
            'fulfillment_score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    lines = content.strip().split('\n')

    # 제목/소제목 추출
    title_keywords = _extract_title_keywords(lines)
    heading_keywords = _extract_heading_keywords(lines)

    all_keywords = title_keywords + heading_keywords

    if not all_keywords:
        return {
            'promises': [],
            'fulfillment_score': 0.0,
            'suggestions': ['제목이나 소제목을 찾을 수 없습니다. 마크다운 헤딩(#)을 사용해 주세요.'],
        }

    # 본문 추출 (제목/소제목 라인 제외)
    body_text = _extract_body(lines)
    body_len = len(body_text)

    # 도입부(첫 20%)와 결론(마지막 20%) 분할
    intro_end = max(1, int(body_len * 0.2))
    conclusion_start = max(intro_end, int(body_len * 0.8))
    intro_text = body_text[:intro_end]
    conclusion_text = body_text[conclusion_start:]

    # 각 약속 키워드 검증
    promises = []
    seen = set()  # 중복 키워드 방지

    for keyword, source in all_keywords:
        if keyword in seen:
            continue
        seen.add(keyword)

        frequency = _count_occurrences(keyword, body_text)
        found_in_body = frequency > 0
        in_intro = _count_occurrences(keyword, intro_text) > 0
        in_conclusion = _count_occurrences(keyword, conclusion_text) > 0

        status = _determine_status(found_in_body, frequency, in_intro, in_conclusion)

        promises.append({
            'keyword': keyword,
            'source': source,
            'found_in_body': found_in_body,
            'frequency': frequency,
            'in_intro': in_intro,
            'in_conclusion': in_conclusion,
            'status': status,
        })

    # 이행 점수 계산
    fulfillment_score = _calculate_score(promises)

    # 제안 생성
    suggestions = _generate_suggestions(promises, fulfillment_score)

    return {
        'promises': promises,
        'fulfillment_score': fulfillment_score,
        'suggestions': suggestions,
    }


def _extract_title_keywords(lines: list) -> list:
    """제목(첫 줄 또는 # 헤딩)에서 키워드를 추출합니다.

    Returns:
        [(keyword, "title"), ...] 형태의 리스트
    """
    title_line = None

    # # 마크다운 제목 찾기
    for line in lines:
        stripped = line.strip()
        if re.match(r'^#\s+', stripped):
            title_line = re.sub(r'^#+\s*', '', stripped)
            break

    # # 헤딩이 없으면 첫 비어있지 않은 줄을 제목으로 간주
    if title_line is None:
        for line in lines:
            stripped = line.strip()
            if stripped:
                title_line = stripped
                break

    if not title_line:
        return []

    keywords = _extract_keywords_from_text(title_line)
    return [(kw, 'title') for kw in keywords]


def _extract_heading_keywords(lines: list) -> list:
    """소제목(## / ###)에서 키워드를 추출합니다.

    Returns:
        [(keyword, "heading"), ...] 형태의 리스트
    """
    results = []
    for line in lines:
        stripped = line.strip()
        # ## 또는 ### 패턴 (# 단일 제목은 제외)
        if re.match(r'^#{2,3}\s+', stripped):
            heading_text = re.sub(r'^#+\s*', '', stripped)
            keywords = _extract_keywords_from_text(heading_text)
            results.extend((kw, 'heading') for kw in keywords)
    return results


def _extract_keywords_from_text(text: str) -> list:
    """텍스트에서 핵심 키워드를 추출합니다.

    한국어 단어(2자+)와 영어 단어(3자+)를 추출하고
    불용어/조사를 제거합니다.
    """
    keywords = []

    # 한국어 단어 추출 (2자 이상)
    korean_words = re.findall(r'[가-힣]{2,}', text)
    for word in korean_words:
        stem = _PARTICLES.sub('', word)
        if len(stem) >= 2 and stem not in _STOPWORDS:
            keywords.append(stem)

    # 영어 단어 추출 (3자 이상)
    english_words = re.findall(r'[A-Za-z]{3,}', text)
    for word in english_words:
        keywords.append(word)

    return keywords


def _extract_body(lines: list) -> str:
    """제목/소제목 라인을 제외한 본문 텍스트를 추출합니다."""
    body_lines = []
    for line in lines:
        stripped = line.strip()
        # 마크다운 헤딩이 아닌 라인만
        if not re.match(r'^#+\s+', stripped):
            body_lines.append(stripped)
    return ' '.join(body_lines)


def _count_occurrences(keyword: str, text: str) -> int:
    """텍스트 내 키워드 등장 횟수를 계산합니다 (대소문자 무시)."""
    pattern = re.escape(keyword)
    return len(re.findall(pattern, text, re.IGNORECASE))


def _determine_status(found: bool, frequency: int, in_intro: bool, in_conclusion: bool) -> str:
    """약속 이행 상태를 판단합니다.

    - fulfilled: 본문에 3회 이상 등장하거나, 2회 이상 + 도입/결론 중 하나에 등장
    - weak: 본문에 등장하지만 빈도가 낮음
    - missing: 본문에 전혀 등장하지 않음
    """
    if not found:
        return 'missing'

    if frequency >= 3:
        return 'fulfilled'

    if frequency >= 2 and (in_intro or in_conclusion):
        return 'fulfilled'

    return 'weak'


def _calculate_score(promises: list) -> float:
    """이행 점수를 계산합니다 (0-100).

    - fulfilled: 100점
    - weak: 40점
    - missing: 0점
    전체 평균을 반환합니다.
    """
    if not promises:
        return 0.0

    status_scores = {
        'fulfilled': 100.0,
        'weak': 40.0,
        'missing': 0.0,
    }

    total = sum(status_scores.get(p['status'], 0.0) for p in promises)
    score = total / len(promises)

    return round(score, 1)


def _generate_suggestions(promises: list, score: float) -> list:
    """검증 결과 기반 개선 제안을 생성합니다."""
    suggestions = []

    missing = [p for p in promises if p['status'] == 'missing']
    weak = [p for p in promises if p['status'] == 'weak']

    if missing:
        keywords_str = ', '.join(f'"{p["keyword"]}"' for p in missing)
        suggestions.append(
            f'다음 키워드가 본문에서 언급되지 않았습니다: {keywords_str}. '
            f'제목/소제목에서 약속한 내용은 반드시 본문에서 다뤄야 합니다.'
        )

    if weak:
        keywords_str = ', '.join(f'"{p["keyword"]}"' for p in weak)
        suggestions.append(
            f'다음 키워드가 충분히 다뤄지지 않았습니다: {keywords_str}. '
            f'해당 주제를 더 상세히 설명하거나 관련 예시를 추가하세요.'
        )

    # 도입부 누락 검사
    not_in_intro = [p for p in promises if p['found_in_body'] and not p['in_intro']]
    if not_in_intro:
        suggestions.append(
            '일부 핵심 키워드가 도입부에 언급되지 않았습니다. '
            '글 초반에 주요 키워드를 언급하면 독자의 기대를 설정하는 데 효과적입니다.'
        )

    # 결론 누락 검사
    not_in_conclusion = [p for p in promises if p['found_in_body'] and not p['in_conclusion']]
    if not_in_conclusion:
        suggestions.append(
            '일부 핵심 키워드가 결론부에 언급되지 않았습니다. '
            '마무리에서 핵심 키워드를 다시 언급하면 메시지를 강화할 수 있습니다.'
        )

    if score == 100.0:
        suggestions.append('모든 약속 키워드가 본문에서 충분히 다뤄지고 있습니다.')

    return suggestions
