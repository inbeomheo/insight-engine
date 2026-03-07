"""
검색 의도 적합도 분석 서비스 (Search Intent Matcher)

콘텐츠와 타겟 키워드의 검색 의도를 규칙 기반으로 분석하고,
콘텐츠가 해당 의도에 적합한 형식인지 점수화합니다.
AI API 호출 없이 순수 규칙 기반으로 동작합니다.

의도 유형:
- informational: 정보 탐색 (무엇, 방법, 이유)
- commercial: 상업적 조사 (비교, 리뷰, 추천)
- transactional: 거래/행동 (구매, 가입, 다운로드)
- navigational: 특정 사이트/브랜드 탐색
"""

import re
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# ─── 의도별 신호 패턴 정의 ───

_INTENT_SIGNALS = {
    'informational': {
        'keyword_groups': [
            # 그룹 1: 정의/개념 질문
            ['무엇', '뜻', '정의', '의미', '개념'],
            # 그룹 2: 방법/가이드
            ['어떻게', '방법', '가이드', '튜토리얼'],
            # 그룹 3: 이유/원인
            ['왜', '이유', '원인'],
            # 그룹 4: 설명형 문장 어미 (패턴 매칭)
            [],
            # 그룹 5: 헤딩/목록 구조
            [],
        ],
        'patterns': [
            # 그룹 4: 설명형 문장 어미
            [r'입니다[.\s]', r'합니다[.\s]', r'됩니다[.\s]', r'있습니다[.\s]'],
            # 그룹 5: 헤딩/목록 구조
            [r'^#{1,6}\s', r'^\d+[\.\)]\s', r'^[-*]\s'],
        ],
    },
    'commercial': {
        'keyword_groups': [
            # 그룹 1: 추천/비교/리뷰
            ['추천', '비교', '리뷰', '평가', '순위'],
            # 그룹 2: 최고/베스트
            ['최고', '베스트', 'TOP', 'vs'],
            # 그룹 3: 장단점/특징/가격
            ['장단점', '특징', '가격'],
            # 그룹 4: 비교 표현 (패턴)
            [],
            # 그룹 5: 평가/별점 패턴
            [],
        ],
        'patterns': [
            # 그룹 4: 비교 표현
            [r'보다\s*(더|낫|좋|우수)', r'대비', r'비해', r'차이점', r'vs\.?'],
            # 그룹 5: 평가/별점
            [r'[★☆⭐]', r'\d+점', r'\d+\/\d+', r'별점', r'평점'],
        ],
    },
    'transactional': {
        'keyword_groups': [
            # 그룹 1: 구매/가입/다운로드
            ['구매', '가입', '다운로드', '신청', '등록'],
            # 그룹 2: 할인/쿠폰/무료
            ['할인', '쿠폰', '무료', '체험', '가격'],
            # 그룹 3: 즉시 행동 (패턴)
            [],
            # 그룹 4: CTA 표현 (패턴)
            [],
            # 그룹 5: 가격/결제 정보 (패턴)
            [],
        ],
        'patterns': [
            # 그룹 3: 즉시 행동
            [r'지금\s*(바로|즉시|당장)', r'바로\s*(시작|구매|가입|신청)',
             r'즉시\s*(다운|받|시작)'],
            # 그룹 4: CTA 표현
            [r'클릭', r'지금\s*확인', r'무료\s*체험', r'시작하세요',
             r'신청하세요', r'가입하세요'],
            # 그룹 5: 가격/결제 정보
            [r'\d+[,.]?\d*\s*원', r'₩\s*\d+', r'결제', r'카드', r'계좌'],
        ],
    },
    'navigational': {
        'keyword_groups': [
            # 그룹 1: 공식/홈페이지 (각 +25)
            ['공식', '홈페이지', '사이트', '로그인'],
            # 그룹 2: URL/링크 (패턴)
            [],
            # 그룹 3: 특정 서비스 집중 (패턴)
            [],
            # 그룹 4: 브랜드명 반복 (별도 로직)
            [],
        ],
        'patterns': [
            # 그룹 2: URL/링크
            [r'https?://', r'www\.', r'\.com', r'\.co\.kr', r'\.net'],
            # 그룹 3: 특정 페이지 안내
            [r'접속', r'방문', r'이동', r'바로가기', r'링크'],
        ],
    },
}

# 의도별 권장 형식
_RECOMMENDED_FORMATS = {
    'informational': '가이드/설명형 콘텐츠',
    'commercial': '비교 리뷰형 콘텐츠',
    'transactional': '전환 유도형 콘텐츠',
    'navigational': '브랜드 안내형 콘텐츠',
}

# navigational 신호 점수 단위 (4개 그룹이므로 +25)
_NAV_SIGNAL_SCORE = 25
# 나머지 의도 신호 점수 단위 (5개 그룹이므로 +20)
_DEFAULT_SIGNAL_SCORE = 20


def _count_keyword_hits(text: str, keywords: List[str]) -> int:
    """텍스트에서 키워드 매칭 횟수를 반환한다."""
    count = 0
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            count += 1
    return count


def _check_patterns(text: str, patterns: List[str]) -> bool:
    """정규식 패턴 중 하나라도 매칭되면 True를 반환한다."""
    for pattern in patterns:
        if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            return True
    return False


def _detect_brand_repetition(text: str) -> bool:
    """
    고유명사(대문자 시작 단어 또는 한글 2~6자 고유명사 후보)가
    2회 이상 반복되는지 감지한다.
    """
    # 영문 대문자 시작 단어 (2자 이상)
    en_proper = re.findall(r'\b[A-Z][a-zA-Z]{1,}\b', text)
    for word in set(en_proper):
        if text.count(word) >= 2:
            return True

    # 한글 고유명사 후보: 따옴표로 감싸진 단어 또는 반복되는 고유 단어
    # 간단히 연속 2자 이상 한글 단어 중 3회 이상 반복되는 것
    ko_words = re.findall(r'[가-힣]{2,6}', text)
    from collections import Counter
    word_counts = Counter(ko_words)
    # 일반적인 조사/어미 제외
    common_words = {'입니다', '합니다', '됩니다', '있습니다', '하는', '이런',
                    '그런', '이것', '그것', '대한', '통해', '위해', '에서',
                    '으로', '부터', '까지', '에는', '것은', '것이', '수가',
                    '하고', '에게', '라고', '한다', '된다', '있는', '없는',
                    '하여', '하면', '되는', '있다', '없다', '않는', '같은',
                    '어떤', '모든', '여러', '다른', '많은', '가장', '이를',
                    '또한', '그리고', '하지만', '그러나', '따라서', '때문에'}
    for word, count in word_counts.items():
        if count >= 3 and word not in common_words and len(word) >= 2:
            return True
    return False


def _calculate_intent_signals(content: str, keyword: str) -> Dict[str, float]:
    """각 의도별 신호 점수를 계산한다."""
    # 분석 대상: 콘텐츠 + 키워드
    combined = f"{keyword} {content}" if keyword else content
    signals = {}

    for intent, config in _INTENT_SIGNALS.items():
        score = 0.0
        score_unit = _NAV_SIGNAL_SCORE if intent == 'navigational' else _DEFAULT_SIGNAL_SCORE
        keyword_groups = config['keyword_groups']
        pattern_groups = config['patterns']

        # 키워드 그룹 매칭
        pattern_idx = 0
        for group in keyword_groups:
            if group:
                # 키워드 기반 그룹
                if _count_keyword_hits(combined, group) > 0:
                    score += score_unit
            else:
                # 패턴 기반 그룹 (keyword_groups에서 빈 리스트는 patterns에서 대응)
                if pattern_idx < len(pattern_groups):
                    if _check_patterns(combined, pattern_groups[pattern_idx]):
                        score += score_unit
                    pattern_idx += 1

        # navigational 특수: 브랜드명 반복 감지
        if intent == 'navigational' and _detect_brand_repetition(combined):
            score += score_unit

        signals[intent] = min(score, 100.0)

    return signals


def _calculate_format_match(content: str, intent: str) -> tuple:
    """
    콘텐츠 형식이 감지된 의도에 맞는지 점수화한다.
    (점수, 문제 목록)을 반환한다.
    """
    score = 0.0
    issues = []
    lines = content.split('\n') if content else []

    if intent == 'informational':
        # 헤딩 3개 이상
        heading_count = sum(1 for line in lines if re.match(r'^#{1,6}\s', line))
        if heading_count >= 3:
            score += 30
        elif heading_count >= 1:
            score += 15
        else:
            issues.append('정보형 콘텐츠에 헤딩(제목) 구조가 부족합니다')

        # 긴 문단 (100자 이상 문단 존재)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        long_paras = sum(1 for p in paragraphs if len(p) >= 100)
        if long_paras >= 2:
            score += 25
        elif long_paras >= 1:
            score += 10
        else:
            issues.append('설명이 충분히 상세하지 않습니다')

        # 정의 포함 ("~란", "~이란", "정의", "의미")
        if re.search(r'(이란|란\s|정의|의미는|개념은)', content):
            score += 25
        else:
            issues.append('핵심 용어의 정의가 포함되면 좋겠습니다')

        # 목록 구조
        list_count = sum(1 for line in lines
                         if re.match(r'^\s*[-*]\s', line) or
                         re.match(r'^\s*\d+[\.\)]\s', line))
        if list_count >= 3:
            score += 20
        elif list_count >= 1:
            score += 10

    elif intent == 'commercial':
        # 비교 표현
        if _check_patterns(content, [r'보다\s*(더|낫|좋)', r'대비', r'비해',
                                      r'차이점', r'vs\.?', r'비교']):
            score += 25
        else:
            issues.append('비교 분석 표현이 부족합니다')

        # 장단점 표현
        if re.search(r'(장점|단점|장단점|pros|cons|강점|약점)', content,
                      re.IGNORECASE):
            score += 25
        else:
            issues.append('장단점 분석이 포함되면 좋겠습니다')

        # 표(테이블) 구조
        if re.search(r'\|.+\|.+\|', content):
            score += 25
        else:
            issues.append('비교표가 있으면 상업적 의도에 더 적합합니다')

        # 평가 기준/점수
        if re.search(r'(평가|점수|별점|평점|\d+\/\d+|[★☆⭐])', content):
            score += 25

    elif intent == 'transactional':
        # CTA (Call to Action)
        if re.search(r'(시작하세요|신청하세요|가입하세요|구매하세요|클릭|지금\s*확인|'
                      r'무료\s*체험|바로\s*시작)', content):
            score += 30
        else:
            issues.append('행동 유도 문구(CTA)가 부족합니다')

        # 가격/혜택 정보
        if re.search(r'(\d+[,.]?\d*\s*원|₩|할인|무료|쿠폰|혜택|특가)', content):
            score += 30
        else:
            issues.append('가격이나 혜택 정보가 포함되면 좋겠습니다')

        # 긴급성/희소성
        if re.search(r'(지금|바로|즉시|한정|마감|선착순|오늘만)', content):
            score += 20

        # 결제/구매 안내
        if re.search(r'(결제|카드|계좌|배송|환불|보장)', content):
            score += 20

    elif intent == 'navigational':
        # 브랜드명 반복
        if _detect_brand_repetition(content):
            score += 30
        else:
            issues.append('브랜드/서비스명이 충분히 언급되지 않았습니다')

        # 기능/서비스 나열
        list_count = sum(1 for line in lines
                         if re.match(r'^\s*[-*]\s', line) or
                         re.match(r'^\s*\d+[\.\)]\s', line))
        if list_count >= 3:
            score += 25
        elif list_count >= 1:
            score += 10

        # URL/링크 포함
        if re.search(r'(https?://|www\.|\.com|\.co\.kr)', content):
            score += 25

        # 공식/홈페이지 표현
        if re.search(r'(공식|홈페이지|사이트|로그인|바로가기)', content):
            score += 20

    return min(score, 100.0), issues


def _generate_suggestions(intent: str, format_score: float,
                           issues: List[str], signals: Dict[str, float]) -> List[str]:
    """의도와 형식 점수에 기반한 개선 제안을 생성한다."""
    suggestions = []

    # 형식 불일치 시 제안
    if format_score < 50:
        fmt = _RECOMMENDED_FORMATS.get(intent, '')
        suggestions.append(f'콘텐츠를 "{fmt}" 형식에 맞게 구성하세요')

    # 의도별 구체적 제안
    if intent == 'informational':
        if signals.get('informational', 0) < 60:
            suggestions.append('설명형 표현(~입니다, ~합니다)과 용어 정의를 추가하세요')
    elif intent == 'commercial':
        if signals.get('commercial', 0) < 60:
            suggestions.append('비교 표현, 장단점 분석, 평가 기준을 추가하세요')
    elif intent == 'transactional':
        if signals.get('transactional', 0) < 60:
            suggestions.append('행동 유도 문구(CTA)와 가격/혜택 정보를 추가하세요')
    elif intent == 'navigational':
        if signals.get('navigational', 0) < 60:
            suggestions.append('브랜드명 반복과 공식 링크를 추가하세요')

    # 형식 이슈를 제안에 추가
    for issue in issues:
        suggestions.append(issue)

    # 신뢰도 낮을 때
    sorted_scores = sorted(signals.values(), reverse=True)
    if len(sorted_scores) >= 2:
        confidence = sorted_scores[0] - sorted_scores[1]
        if confidence < 20:
            suggestions.append('검색 의도가 명확하지 않습니다. 타겟 키워드를 더 구체적으로 설정하세요')

    return suggestions


def analyze_search_intent(content: str, target_keyword: str = '') -> dict:
    """
    콘텐츠와 타겟 키워드의 검색 의도를 분석하고 적합도를 점수화한다.

    Args:
        content: 분석할 콘텐츠 텍스트
        target_keyword: 타겟 검색 키워드 (선택)

    Returns:
        검색 의도 분석 결과 딕셔너리
    """
    # 빈 콘텐츠 처리
    if not content or not content.strip():
        return {
            'detected_intent': 'informational',
            'intent_confidence': 0.0,
            'intent_signals': {
                'informational': 0.0,
                'commercial': 0.0,
                'transactional': 0.0,
                'navigational': 0.0,
            },
            'content_format_match': 0.0,
            'format_issues': ['콘텐츠가 비어 있습니다'],
            'recommended_format': _RECOMMENDED_FORMATS['informational'],
            'suggestions': ['콘텐츠를 작성한 후 다시 분석하세요'],
        }

    keyword = target_keyword.strip() if target_keyword else ''

    # 1. 의도별 신호 점수 계산
    signals = _calculate_intent_signals(content, keyword)

    # 2. 최고 점수 의도 감지
    sorted_intents = sorted(signals.items(), key=lambda x: x[1], reverse=True)
    detected_intent = sorted_intents[0][0]
    top_score = sorted_intents[0][1]
    second_score = sorted_intents[1][1] if len(sorted_intents) > 1 else 0.0

    # 3. 신뢰도: 최고 점수 - 두 번째 점수
    intent_confidence = min(top_score - second_score, 100.0)

    # 모든 점수가 0이면 기본값 informational
    if top_score == 0:
        detected_intent = 'informational'
        intent_confidence = 0.0

    # 4. 콘텐츠 형식 매칭
    format_score, format_issues = _calculate_format_match(content, detected_intent)

    # 5. 권장 형식
    recommended_format = _RECOMMENDED_FORMATS.get(detected_intent,
                                                   '가이드/설명형 콘텐츠')

    # 6. 제안 생성
    suggestions = _generate_suggestions(detected_intent, format_score,
                                         format_issues, signals)

    result = {
        'detected_intent': detected_intent,
        'intent_confidence': intent_confidence,
        'intent_signals': signals,
        'content_format_match': format_score,
        'format_issues': format_issues,
        'recommended_format': recommended_format,
        'suggestions': suggestions,
    }

    logger.debug("검색 의도 분석 완료: intent=%s, confidence=%.1f, format_match=%.1f",
                 detected_intent, intent_confidence, format_score)

    return result
