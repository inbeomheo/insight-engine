"""
현지화 준비도 검사 서비스

콘텐츠의 현지화(i18n/l10n) 준비 상태를 검사합니다.
하드코딩된 날짜/통화/측정단위/문화 참조 등을 감지.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 하드코딩 날짜 형식 (한국어 특화)
_DATE_FORMATS = [
    re.compile(r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일'),   # 2026년 4월 17일
    re.compile(r'\d{4}\.\d{1,2}\.\d{1,2}'),              # 2026.04.17
    re.compile(r'\d{4}/\d{1,2}/\d{1,2}'),                # 2026/04/17
]

# 통화 기호/단위
_CURRENCY_PATTERNS = [
    re.compile(r'\d[\d,]*\s*원(?!\w)'),                   # 10,000원
    re.compile(r'\$\s*[\d,.]+'),                          # $100
    re.compile(r'€\s*[\d,.]+'),                           # €100
    re.compile(r'¥\s*[\d,.]+'),                           # ¥100
    re.compile(r'£\s*[\d,.]+'),                           # £100
]

# 측정 단위
_MEASUREMENT_PATTERNS = [
    re.compile(r'\d+\s*(km|kg|cm|mm|ml|g|m|lb|oz|inch|ft|mile)', re.IGNORECASE),
]

# 문화/지역 특화 참조
_CULTURAL_REFS = {
    'korean_holidays': re.compile(r'(설날|추석|광복절|한글날|삼일절|현충일|개천절)'),
    'korean_food': re.compile(r'(김치|불고기|비빔밥|떡볶이|삼겹살|소주)'),
    'korean_education': re.compile(r'(수능|고3|대입|내신|학원|과외)'),
    'phone_format': re.compile(r'010-\d{4}-\d{4}'),
    'address_format': re.compile(r'(서울|부산|대구|인천|광주|대전|울산)(?:시|특별시|광역시)'),
}

# 시간 표현
_TIME_PATTERNS = [
    re.compile(r'(오전|오후)\s*\d{1,2}시'),
    re.compile(r'\d{1,2}:\d{2}\s*(AM|PM|am|pm)'),
]


def check_localization(content: str, target_locales: List[str] = None) -> dict:
    """콘텐츠의 현지화 준비도를 검사합니다.

    Args:
        content: 검사할 콘텐츠
        target_locales: 대상 로케일 목록 (정보성, 검사 결과에 포함)

    Returns:
        {
            'score': float (0.0~1.0, 높을수록 현지화 친화적),
            'findings': [{'category': str, 'text': str, 'suggestion': str}],
            'summary': {'dates': int, 'currencies': int, 'measurements': int,
                       'cultural_refs': int, 'time_formats': int},
            'ready_for_localization': bool,
            'target_locales': [str],
        }
    """
    if not content or not content.strip():
        return _empty_result(target_locales)

    text = content.strip()
    findings: List[dict] = []
    summary = {'dates': 0, 'currencies': 0, 'measurements': 0,
               'cultural_refs': 0, 'time_formats': 0}

    # 날짜 형식 검사
    for pattern in _DATE_FORMATS:
        matches = pattern.findall(text)
        if matches:
            summary['dates'] += len(matches)
            for m in matches[:3]:
                findings.append({
                    'category': 'date',
                    'text': m,
                    'suggestion': '날짜를 ISO 8601 형식(YYYY-MM-DD)이나 현지화 함수로 변환하세요',
                })

    # 통화 검사
    for pattern in _CURRENCY_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            summary['currencies'] += len(matches)
            for m in matches[:3]:
                findings.append({
                    'category': 'currency',
                    'text': m,
                    'suggestion': '통화를 로케일별 포맷 함수로 처리하세요',
                })

    # 측정 단위 검사
    for pattern in _MEASUREMENT_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            summary['measurements'] += len(matches)

    # 문화 참조 검사
    for ref_name, pattern in _CULTURAL_REFS.items():
        matches = pattern.findall(text)
        if matches:
            summary['cultural_refs'] += len(matches)
            for m in matches[:2]:
                findings.append({
                    'category': 'cultural',
                    'text': m,
                    'suggestion': f'문화 특화 참조 ({ref_name}): 대상 로케일에 맞게 설명을 추가하거나 대체하세요',
                })

    # 시간 형식 검사
    for pattern in _TIME_PATTERNS:
        matches = pattern.findall(text)
        if matches:
            summary['time_formats'] += len(matches)

    total_issues = sum(summary.values())
    # 이슈가 적을수록 높은 점수
    word_count = len(re.findall(r'[\w가-힣]+', text))
    density = total_issues / max(1, word_count / 100)  # 100단어당 이슈 수
    score = round(max(0.0, min(1.0, 1.0 - density * 0.15)), 2)

    return {
        'score': score,
        'findings': findings[:20],  # 최대 20개
        'summary': summary,
        'ready_for_localization': score >= 0.7 and summary['cultural_refs'] == 0,
        'target_locales': target_locales or [],
    }


def _empty_result(target_locales=None) -> dict:
    return {
        'score': 1.0,
        'findings': [],
        'summary': {'dates': 0, 'currencies': 0, 'measurements': 0,
                    'cultural_refs': 0, 'time_formats': 0},
        'ready_for_localization': True,
        'target_locales': target_locales or [],
    }
