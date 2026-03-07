"""
Subheading Gap Detector 서비스

마크다운 헤딩(#, ##, ###) 사이 텍스트가
너무 길거나 불균형한 섹션 분할을 감지합니다.
"""
import re
import math
import logging

logger = logging.getLogger(__name__)

# 섹션 길이 임계값 (글자 수 기준)
_TOO_LONG_THRESHOLD = 300
_TOO_SHORT_THRESHOLD = 50


def detect_subheading_gaps(content: str) -> dict:
    """마크다운 콘텐츠의 헤딩 간 불균형을 분석합니다.

    Args:
        content: 분석할 마크다운 콘텐츠

    Returns:
        {
            "sections": [{"heading": str, "level": int, "word_count": int,
                          "char_count": int, "paragraph_count": int, "status": str}],
            "gaps": [{"after_heading": str, "char_count": int, "issue": str}],
            "balance_score": float,  # 0-100
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'sections': [],
            'gaps': [],
            'balance_score': 100.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 섹션 분할
    sections = _split_sections(content)

    if not sections:
        return {
            'sections': [],
            'gaps': [],
            'balance_score': 100.0,
            'suggestions': ['헤딩이 없습니다. 마크다운 헤딩(#, ##, ###)을 추가해 주세요.'],
        }

    # 각 섹션 분석
    analyzed = [_analyze_section(s) for s in sections]

    # 갭(문제) 감지
    gaps = _detect_gaps(analyzed)

    # 균형 점수 계산
    balance_score = _calculate_balance_score(analyzed)

    # 개선 제안
    suggestions = _generate_suggestions(analyzed, gaps, balance_score)

    return {
        'sections': analyzed,
        'gaps': gaps,
        'balance_score': balance_score,
        'suggestions': suggestions,
    }


def _split_sections(content: str) -> list:
    """마크다운 헤딩 기준으로 섹션을 분할합니다."""
    # 헤딩 패턴: 줄 시작의 #{1,6} + 공백 + 텍스트
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    matches = list(heading_pattern.finditer(content))
    if not matches:
        return []

    sections = []
    for i, match in enumerate(matches):
        heading_text = match.group(2).strip()
        level = len(match.group(1))

        # 본문: 현재 헤딩 다음부터 다음 헤딩(또는 끝)까지
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[body_start:body_end].strip()

        sections.append({
            'heading': heading_text,
            'level': level,
            'body': body,
        })

    return sections


def _analyze_section(section: dict) -> dict:
    """개별 섹션의 통계를 계산합니다."""
    body = section['body']

    # 글자 수: 공백 제외
    char_count = len(re.sub(r'\s+', '', body))

    # 단어 수: 한국어(2자+) + 영어 단어 합산
    korean_words = re.findall(r'[가-힣]{2,}', body)
    english_words = re.findall(r'[A-Za-z]+', body)
    word_count = len(korean_words) + len(english_words)

    # 단락 수: 빈 줄로 구분
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
    paragraph_count = max(len(paragraphs), 1) if body else 0

    # 상태 판정
    if char_count > _TOO_LONG_THRESHOLD:
        status = 'too_long'
    elif char_count < _TOO_SHORT_THRESHOLD:
        status = 'too_short'
    else:
        status = 'ok'

    return {
        'heading': section['heading'],
        'level': section['level'],
        'word_count': word_count,
        'char_count': char_count,
        'paragraph_count': paragraph_count,
        'status': status,
    }


def _detect_gaps(sections: list) -> list:
    """문제가 있는 섹션을 감지합니다."""
    gaps = []

    for s in sections:
        if s['status'] == 'too_long':
            gaps.append({
                'after_heading': s['heading'],
                'char_count': s['char_count'],
                'issue': f'섹션이 너무 깁니다 ({s["char_count"]}자). '
                         f'하위 헤딩으로 분할을 권장합니다.',
            })
        elif s['status'] == 'too_short':
            gaps.append({
                'after_heading': s['heading'],
                'char_count': s['char_count'],
                'issue': f'섹션이 너무 짧습니다 ({s["char_count"]}자). '
                         f'내용을 보강하거나 인접 섹션과 병합을 권장합니다.',
            })

    return gaps


def _calculate_balance_score(sections: list) -> float:
    """섹션 간 균형 점수를 계산합니다 (0-100).

    - 글자 수 표준편차가 낮을수록 균형적
    - 모든 섹션이 ok 상태면 가산점
    """
    if not sections:
        return 100.0

    if len(sections) == 1:
        # 단일 섹션: 상태에 따라 점수 부여
        return 100.0 if sections[0]['status'] == 'ok' else 50.0

    char_counts = [s['char_count'] for s in sections]
    mean = sum(char_counts) / len(char_counts)

    if mean == 0:
        return 100.0

    # 변동계수(CV) 기반 점수: CV가 0이면 100점, 높을수록 감점
    variance = sum((c - mean) ** 2 for c in char_counts) / len(char_counts)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean  # 변동계수

    # CV 0 → 100점, CV 1.0 → 30점, CV 2.0+ → 0점
    base_score = max(0.0, 100.0 - (cv * 70.0))

    # 문제 섹션 비율에 따라 감점
    problem_count = sum(1 for s in sections if s['status'] != 'ok')
    penalty = (problem_count / len(sections)) * 20.0

    score = max(0.0, min(100.0, base_score - penalty))
    return round(score, 1)


def _generate_suggestions(sections: list, gaps: list, balance_score: float) -> list:
    """분석 결과 기반 개선 제안을 생성합니다."""
    suggestions = []

    if not sections:
        return suggestions

    too_long = [s for s in sections if s['status'] == 'too_long']
    too_short = [s for s in sections if s['status'] == 'too_short']

    if too_long:
        suggestions.append(
            f'{len(too_long)}개 섹션이 {_TOO_LONG_THRESHOLD}자를 초과합니다. '
            f'하위 헤딩(##, ###)으로 분할하세요.'
        )

    if too_short:
        suggestions.append(
            f'{len(too_short)}개 섹션이 {_TOO_SHORT_THRESHOLD}자 미만입니다. '
            f'내용을 보강하거나 인접 섹션과 병합하세요.'
        )

    if balance_score < 50:
        suggestions.append(
            '섹션 간 길이 불균형이 심합니다. '
            '각 섹션의 분량을 비슷하게 조정해 주세요.'
        )

    if not gaps and balance_score >= 80:
        suggestions.append('섹션 구조가 양호합니다.')

    return suggestions
