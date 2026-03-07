"""
Consistency & Contradiction Checker 서비스

문서 내부의 수치, 날짜, 고유명사, 비교 표현이
서로 충돌하는 구간을 찾아 보고합니다.
AI API 호출 없이 순수 Python(re, collections)으로 동작합니다.
"""
import re
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

# --- 정규표현식 패턴 ---

# 숫자 + 단위 (예: 100억, 30%, 5,000만, 3.5배)
_NUMBER_UNIT_RE = re.compile(
    r'(\d[\d,.]*)\s*(억|만|천|조|%|퍼센트|배|개|명|원|달러|달라|건|회|년|개월|일|시간|분|초|위|등|kg|km|m|cm|g|GB|MB|TB)?'
)

# 연도 (4자리: 1900~2099)
_YEAR_RE = re.compile(r'\b((?:19|20)\d{2})\s*년?')

# 날짜 (YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD, MM월 DD일)
_DATE_RE = re.compile(
    r'(?:(\d{4})[./\-](\d{1,2})[./\-](\d{1,2}))'
    r'|(?:(\d{1,2})월\s*(\d{1,2})일)'
)

# 비교 표현
_COMPARISON_PATTERNS = [
    # "A가 B보다 크다/높다/많다/좋다/빠르다/우수하다"
    re.compile(r'([가-힣A-Za-z0-9]+)[이가은는]\s+([가-힣A-Za-z0-9]+)보다\s+(크|높|많|좋|빠르|우수|뛰어나|앞서|강하)'),
    # "A에 비해 B가 ..."
    re.compile(r'([가-힣A-Za-z0-9]+)에\s*비해\s+([가-힣A-Za-z0-9]+)[이가은는]?\s+(크|높|많|좋|빠르|우수|뛰어나|앞서|강하)'),
    # "A 대비 B"
    re.compile(r'([가-힣A-Za-z0-9]+)\s*대비\s+([가-힣A-Za-z0-9]+)[이가은는]?\s+(크|높|많|좋|빠르|우수|뛰어나|앞서|강하)'),
]

# 주제어 근접 범위 (문자 수)
_CONTEXT_WINDOW = 30

# 주제 키워드 추출용 조사 패턴 (모듈 레벨 사전컴파일)
_TOPIC_PARTICLES = re.compile(r'(은|는|이|가|을|를|의|에|와|과|도|로|으로)$')


def check_consistency(content: str) -> dict:
    """콘텐츠 내부의 모순/불일치를 감지합니다.

    Args:
        content: 분석할 텍스트

    Returns:
        {
            "conflicts": [{"type": str, "text1": str, "text2": str,
                           "sentence1": str, "sentence2": str, "severity": str}],
            "consistency_score": float,  # 0-100
            "suggestions": list[str]
        }
    """
    if not content or not content.strip():
        return {
            'conflicts': [],
            'consistency_score': 100.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 문장 분리
    sentences = _split_sentences(content)

    conflicts = []

    # 4가지 유형 감지
    conflicts.extend(_detect_number_conflicts(sentences))
    conflicts.extend(_detect_date_conflicts(sentences))
    conflicts.extend(_detect_comparison_conflicts(sentences))
    conflicts.extend(_detect_name_conflicts(sentences))

    # 중복 제거
    conflicts = _deduplicate(conflicts)

    # 일관성 점수 계산
    score = _calculate_score(conflicts, len(sentences))

    # 개선 제안 생성
    suggestions = _build_suggestions(conflicts)

    return {
        'conflicts': conflicts,
        'consistency_score': score,
        'suggestions': suggestions,
    }


# --- 문장 분리 ---

def _split_sentences(content: str) -> list:
    """텍스트를 문장 단위로 분리합니다."""
    # 마침표/물음표/느낌표 또는 줄바꿈으로 분리
    raw = re.split(r'(?<=[.!?。])\s+|\n+', content)
    return [s.strip() for s in raw if len(s.strip()) >= 5]


# --- 수치 모순 감지 ---

def _extract_number_facts(sentence: str) -> list:
    """문장에서 (주제 컨텍스트, 숫자값, 단위, 원문) 튜플을 추출합니다."""
    facts = []
    for m in _NUMBER_UNIT_RE.finditer(sentence):
        num_str = m.group(1).replace(',', '')
        unit = m.group(2) or ''

        try:
            value = float(num_str)
        except ValueError:
            continue

        # 주제 컨텍스트: 숫자 앞뒤 N자
        start = max(0, m.start() - _CONTEXT_WINDOW)
        end = min(len(sentence), m.end() + _CONTEXT_WINDOW)
        context = sentence[start:end]

        original = m.group(0)
        facts.append((context, value, unit, original))

    return facts


def _extract_topic_keywords(context: str) -> set:
    """컨텍스트에서 주제 키워드를 추출합니다."""
    # 한국어 2자 이상 명사 + 영어 3자 이상
    kr = set(re.findall(r'[가-힣]{2,}', context))
    en = set(w.lower() for w in re.findall(r'[A-Za-z]{3,}', context))
    # 조사 제거 (모듈 레벨 사전컴파일 패턴 사용)
    kr = {_TOPIC_PARTICLES.sub('', w) for w in kr if len(_TOPIC_PARTICLES.sub('', w)) >= 2}
    return kr | en


def _topics_overlap(ctx1: str, ctx2: str) -> bool:
    """두 컨텍스트가 같은 주제를 다루는지 확인합니다."""
    kw1 = _extract_topic_keywords(ctx1)
    kw2 = _extract_topic_keywords(ctx2)
    if not kw1 or not kw2:
        return False
    overlap = kw1 & kw2
    # 공통 키워드가 최소 1개 이상이면 같은 주제
    return len(overlap) >= 1


def _detect_number_conflicts(sentences: list) -> list:
    """서로 다른 문장에서 같은 주제의 수치가 다른 경우를 감지합니다."""
    conflicts = []
    # 문장별 수치 팩트 수집
    sentence_facts = []
    for sent in sentences:
        facts = _extract_number_facts(sent)
        if facts:
            sentence_facts.append((sent, facts))

    # 모든 문장 쌍 비교
    for i in range(len(sentence_facts)):
        sent1, facts1 = sentence_facts[i]
        for j in range(i + 1, len(sentence_facts)):
            sent2, facts2 = sentence_facts[j]
            if sent1 == sent2:
                continue

            for ctx1, val1, unit1, text1 in facts1:
                for ctx2, val2, unit2, text2 in facts2:
                    # 같은 단위, 같은 주제, 다른 수치
                    if unit1 == unit2 and val1 != val2 and _topics_overlap(ctx1, ctx2):
                        severity = _number_severity(val1, val2)
                        conflicts.append({
                            'type': 'number_conflict',
                            'text1': text1,
                            'text2': text2,
                            'sentence1': sent1,
                            'sentence2': sent2,
                            'severity': severity,
                        })

    return conflicts


def _number_severity(v1: float, v2: float) -> str:
    """수치 차이에 따른 심각도를 반환합니다."""
    if v1 == 0 or v2 == 0:
        return 'high'
    ratio = max(v1, v2) / min(v1, v2)
    if ratio >= 2.0:
        return 'high'
    elif ratio >= 1.3:
        return 'medium'
    return 'low'


# --- 날짜 모순 감지 ---

def _extract_date_facts(sentence: str) -> list:
    """문장에서 (주제 컨텍스트, 날짜 문자열, 원문) 튜플을 추출합니다."""
    facts = []

    # 연도 추출
    for m in _YEAR_RE.finditer(sentence):
        start = max(0, m.start() - _CONTEXT_WINDOW)
        end = min(len(sentence), m.end() + _CONTEXT_WINDOW)
        context = sentence[start:end]
        facts.append((context, m.group(1), m.group(0)))

    # 날짜 추출
    for m in _DATE_RE.finditer(sentence):
        start = max(0, m.start() - _CONTEXT_WINDOW)
        end = min(len(sentence), m.end() + _CONTEXT_WINDOW)
        context = sentence[start:end]
        date_str = m.group(0)
        facts.append((context, date_str, date_str))

    return facts


def _detect_date_conflicts(sentences: list) -> list:
    """서로 다른 문장에서 같은 이벤트의 날짜가 다른 경우를 감지합니다."""
    conflicts = []
    sentence_facts = []
    for sent in sentences:
        facts = _extract_date_facts(sent)
        if facts:
            sentence_facts.append((sent, facts))

    for i in range(len(sentence_facts)):
        sent1, facts1 = sentence_facts[i]
        for j in range(i + 1, len(sentence_facts)):
            sent2, facts2 = sentence_facts[j]
            if sent1 == sent2:
                continue

            for ctx1, date1, text1 in facts1:
                for ctx2, date2, text2 in facts2:
                    # 같은 주제, 다른 날짜
                    if date1 != date2 and _topics_overlap(ctx1, ctx2):
                        conflicts.append({
                            'type': 'date_conflict',
                            'text1': text1,
                            'text2': text2,
                            'sentence1': sent1,
                            'sentence2': sent2,
                            'severity': 'high',
                        })

    return conflicts


# --- 비교 방향 모순 감지 ---

def _extract_comparisons(sentence: str) -> list:
    """문장에서 (A, B, 방향) 비교 튜플을 추출합니다."""
    comparisons = []
    for pattern in _COMPARISON_PATTERNS:
        for m in pattern.finditer(sentence):
            a = m.group(1)
            b = m.group(2)
            # 방향: A > B
            comparisons.append((a, b, 'greater'))
    return comparisons


def _detect_comparison_conflicts(sentences: list) -> list:
    """비교 방향이 모순되는 경우를 감지합니다."""
    conflicts = []
    sentence_comps = []
    for sent in sentences:
        comps = _extract_comparisons(sent)
        if comps:
            sentence_comps.append((sent, comps))

    for i in range(len(sentence_comps)):
        sent1, comps1 = sentence_comps[i]
        for j in range(i + 1, len(sentence_comps)):
            sent2, comps2 = sentence_comps[j]

            for a1, b1, _ in comps1:
                for a2, b2, _ in comps2:
                    # A>B vs B>A — 방향 반전
                    if a1 == b2 and b1 == a2:
                        conflicts.append({
                            'type': 'comparison_conflict',
                            'text1': f'{a1} > {b1}',
                            'text2': f'{a2} > {b2}',
                            'sentence1': sent1,
                            'sentence2': sent2,
                            'severity': 'high',
                        })

    return conflicts


# --- 고유명사 모순 감지 ---

# 대문자 영어 약어 + 전체명 매핑 시도
_ABBREV_RE = re.compile(r'\b([A-Z]{2,})\b')
_PAREN_FULL_RE = re.compile(r'([가-힣A-Za-z\s]+)\s*\(\s*([A-Z]{2,})\s*\)')
_PAREN_FULL_RE2 = re.compile(r'([A-Z]{2,})\s*\(\s*([가-힣A-Za-z\s]+)\s*\)')


def _detect_name_conflicts(sentences: list) -> list:
    """같은 약어가 서로 다른 전체명으로 풀려 있는 경우를 감지합니다."""
    conflicts = []

    # 약어 → [(전체명, 문장)] 수집
    abbrev_map = defaultdict(list)

    for sent in sentences:
        # 패턴1: "전체명 (약어)"
        for m in _PAREN_FULL_RE.finditer(sent):
            full_name = m.group(1).strip()
            abbrev = m.group(2).strip()
            abbrev_map[abbrev].append((full_name, sent))

        # 패턴2: "약어 (전체명)"
        for m in _PAREN_FULL_RE2.finditer(sent):
            abbrev = m.group(1).strip()
            full_name = m.group(2).strip()
            abbrev_map[abbrev].append((full_name, sent))

    # 같은 약어에 다른 전체명이 있으면 모순
    for abbrev, entries in abbrev_map.items():
        seen = {}
        for full_name, sent in entries:
            normalized = full_name.lower().replace(' ', '')
            if normalized not in seen:
                seen[normalized] = (full_name, sent)
            # 여기서는 수집만

        if len(seen) > 1:
            items = list(seen.values())
            for k in range(len(items)):
                for l in range(k + 1, len(items)):
                    name1, sent1 = items[k]
                    name2, sent2 = items[l]
                    conflicts.append({
                        'type': 'name_conflict',
                        'text1': f'{abbrev} = {name1}',
                        'text2': f'{abbrev} = {name2}',
                        'sentence1': sent1,
                        'sentence2': sent2,
                        'severity': 'medium',
                    })

    return conflicts


# --- 유틸리티 ---

def _deduplicate(conflicts: list) -> list:
    """중복 충돌을 제거합니다."""
    seen = set()
    result = []
    for c in conflicts:
        key = (c['type'], c['text1'], c['text2'])
        rev_key = (c['type'], c['text2'], c['text1'])
        if key not in seen and rev_key not in seen:
            seen.add(key)
            result.append(c)
    return result


def _calculate_score(conflicts: list, sentence_count: int) -> float:
    """일관성 점수를 계산합니다 (0-100)."""
    if not conflicts:
        return 100.0

    # 심각도별 감점
    penalty = 0.0
    for c in conflicts:
        sev = c.get('severity', 'low')
        if sev == 'high':
            penalty += 15.0
        elif sev == 'medium':
            penalty += 10.0
        else:
            penalty += 5.0

    score = max(0.0, 100.0 - penalty)
    return round(score, 1)


def _build_suggestions(conflicts: list) -> list:
    """감지된 모순에 대한 개선 제안을 생성합니다."""
    if not conflicts:
        return ['모순이 발견되지 않았습니다. 콘텐츠의 일관성이 양호합니다.']

    suggestions = []

    # 유형별 제안
    types_found = {c['type'] for c in conflicts}

    if 'number_conflict' in types_found:
        suggestions.append('수치가 불일치하는 구간이 있습니다. 동일 주제에 대한 숫자를 통일해 주세요.')

    if 'date_conflict' in types_found:
        suggestions.append('날짜/연도가 불일치하는 구간이 있습니다. 정확한 날짜를 확인하고 통일해 주세요.')

    if 'comparison_conflict' in types_found:
        suggestions.append('비교 방향이 모순되는 구간이 있습니다. A>B와 B>A가 동시에 기술되어 있는지 확인해 주세요.')

    if 'name_conflict' in types_found:
        suggestions.append('같은 약어가 서로 다른 전체명으로 사용되고 있습니다. 통일된 명칭을 사용해 주세요.')

    # 심각도별 요약
    high_count = sum(1 for c in conflicts if c['severity'] == 'high')
    if high_count > 0:
        suggestions.append(f'심각도 높음(high) 모순이 {high_count}건 있습니다. 우선적으로 수정해 주세요.')

    return suggestions
