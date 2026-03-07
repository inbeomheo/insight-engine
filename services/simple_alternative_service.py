"""
Simple Alternative Finder 서비스

저빈도·고난도 어휘를 쉬운 대체어 사전으로 표시하여
가독성과 대중성을 높이는 규칙 기반 서비스입니다.
AI API 호출 없음.
"""
import re
from typing import List, Dict


# ── 한국어 고난도 어휘 → 쉬운 대체어 사전 ──
_KO_ALTERNATIVES = {
    '상기': '위의/앞서 언급한',
    '하기': '아래의',
    '당해': '해당/그',
    '금번': '이번',
    '차후': '앞으로/이후',
    '전술한': '앞서 말한',
    '후술할': '뒤에서 설명할',
    '가급적': '되도록/가능하면',
    '불가피하게': '어쩔 수 없이',
    '상이하다': '다르다',
    '동일하다': '같다',
    '수반하다': '따르다/함께하다',
    '야기하다': '일으키다/초래하다',
    '도모하다': '꾀하다/추구하다',
    '제고하다': '높이다/향상시키다',
    '간주하다': '여기다/보다',
    '수행하다': '하다/실행하다',
    '활용하다': '쓰다/사용하다',
    '구비하다': '갖추다',
    '산출하다': '계산하다/내다',
    '상충하다': '부딪치다/충돌하다',
    '부합하다': '맞다/일치하다',
    '이행하다': '실천하다/따르다',
    '검토하다': '살펴보다',
    '취합하다': '모으다',
    '잔여': '남은',
    '제반': '모든/여러',
    '소정의': '정해진',
    '상응하는': '맞는/알맞은',
    '여하한': '어떠한',
    '지양하다': '피하다/삼가다',
    '지향하다': '추구하다/목표로 하다',
    '명시하다': '밝히다/적다',
    '유의하다': '주의하다/조심하다',
    '숙지하다': '잘 알다/익히다',
    '병행하다': '함께 하다',
    '부여하다': '주다',
    '기술하다': '쓰다/설명하다',
    '경과하다': '지나다',
}

# ── 영어 고난도 어휘 → 쉬운 대체어 사전 ──
_EN_ALTERNATIVES = {
    'utilize': 'use',
    'implement': 'set up/do',
    'facilitate': 'help/make easier',
    'commence': 'start/begin',
    'terminate': 'end/stop',
    'endeavor': 'try',
    'procure': 'get/buy',
    'ascertain': 'find out',
    'ameliorate': 'improve',
    'elucidate': 'explain/clarify',
    'subsequently': 'then/after',
    'consequently': 'so/as a result',
    'notwithstanding': 'despite/even though',
    'aforementioned': 'mentioned above',
    'henceforth': 'from now on',
    'heretofore': 'until now',
    'pursuant': 'following/according to',
    'whereby': 'by which',
    'wherein': 'in which',
    'thereof': 'of that',
    'pertaining': 'about/related to',
    'cognizant': 'aware',
    'exacerbate': 'worsen/make worse',
    'proliferate': 'spread/increase',
    'juxtapose': 'compare/place side by side',
    'expedite': 'speed up',
    'mitigate': 'reduce/lessen',
    'substantiate': 'prove/support',
    'delineate': 'describe/outline',
    'promulgate': 'announce/make known',
}

# 컴파일된 패턴 (한국어: 어근만 매칭, 영어: 단어 경계)
_KO_PATTERNS = {
    word: (re.compile(re.escape(word)), alt)
    for word, alt in _KO_ALTERNATIVES.items()
}

_EN_PATTERNS = {
    word: (re.compile(r'\b' + re.escape(word) + r'\w*\b', re.IGNORECASE), alt)
    for word, alt in _EN_ALTERNATIVES.items()
}


def find_simple_alternatives(content: str) -> dict:
    """콘텐츠에서 고난도 어휘를 찾아 쉬운 대체어를 제안합니다.

    Args:
        content: 분석할 텍스트 콘텐츠

    Returns:
        findings, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'findings': [],
            'summary': {'total_complex': 0, 'korean_complex': 0, 'english_complex': 0},
            'score': 100.0,
            'suggestions': [],
        }

    findings = []
    seen = set()

    # 한국어 고난도 어휘 탐색
    for word, (pattern, alternative) in _KO_PATTERNS.items():
        matches = pattern.findall(content)
        if matches and word not in seen:
            seen.add(word)
            findings.append({
                'word': word,
                'language': 'korean',
                'count': len(matches),
                'alternative': alternative,
            })

    # 영어 고난도 어휘 탐색
    for word, (pattern, alternative) in _EN_PATTERNS.items():
        matches = pattern.findall(content)
        if matches and word not in seen:
            seen.add(word)
            findings.append({
                'word': word,
                'language': 'english',
                'count': len(matches),
                'alternative': alternative,
            })

    findings.sort(key=lambda f: f['count'], reverse=True)

    ko_count = sum(1 for f in findings if f['language'] == 'korean')
    en_count = sum(1 for f in findings if f['language'] == 'english')
    total = len(findings)

    # 단어 수 계산
    word_count = len(re.findall(r'[A-Za-z]+|[가-힣]+', content))
    complex_ratio = (total / word_count * 100) if word_count > 0 else 0.0

    # 점수: 복잡 어휘 비율이 낮을수록 높음
    if complex_ratio <= 1.0:
        score = 100.0
    elif complex_ratio <= 3.0:
        score = 100.0 - (complex_ratio - 1.0) * 15.0
    else:
        score = max(0.0, 70.0 - (complex_ratio - 3.0) * 10.0)
    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(findings, total, complex_ratio)

    return {
        'findings': findings,
        'summary': {
            'total_complex': total,
            'korean_complex': ko_count,
            'english_complex': en_count,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(findings: List[Dict], total: int, ratio: float) -> List[str]:
    """분석 결과 기반 제안을 생성합니다."""
    suggestions = []
    if total == 0:
        return suggestions

    if total >= 5:
        suggestions.append(
            f'고난도 어휘가 {total}개 발견되었습니다. '
            f'대중 독자를 위해 쉬운 표현으로 교체를 권장합니다.'
        )
    elif total >= 1:
        suggestions.append(
            f'고난도 어휘 {total}개가 있습니다. 필요시 쉬운 대체어를 고려하세요.'
        )

    # 가장 많이 반복되는 고난도 어휘
    top = findings[:3]
    for f in top:
        if f['count'] >= 2:
            suggestions.append(
                f'"{f["word"]}"이(가) {f["count"]}회 사용됨 → "{f["alternative"]}"로 교체 고려'
            )
    return suggestions
