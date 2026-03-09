"""
문화 적합성 서비스.

대상 문화권에 맞는 콘텐츠 적합성을 검사한다.
"""

from dataclasses import dataclass, field
import re
import uuid


@dataclass
class CulturalIssue:
    """문화 이슈"""
    issue_type: str = ""  # idiom / reference / taboo / format
    description: str = ""
    suggestion: str = ""
    target_culture: str = ""


@dataclass
class CulturalReport:
    """문화 적합성 보고서"""
    content_id: str = ""
    target_culture: str = ""
    issues: list = field(default_factory=list)
    fitness_score: float = 1.0


# 문화권별 관용구 호환성 (해당 문화에서 이해하기 어려운 표현)
_CULTURE_IDIOMS = {
    "ko": {
        "break a leg": "영어 관용구 '행운을 빌어' — 한국 독자에게 생소할 수 있음",
        "piece of cake": "영어 관용구 '쉬운 일' — '식은 죽 먹기'로 대체 권장",
        "raining cats and dogs": "영어 관용구 '폭우' — 직역 시 혼란 가능",
    },
    "en": {
        "눈치": "한국 문화 특유 개념 — 'social awareness' 등으로 설명 필요",
        "한": "한국 문화 특유 감정 — 설명 없이 사용 시 이해 어려움",
        "빨리빨리": "한국 문화 특유 표현 — 'hurry culture' 등으로 번역 권장",
    },
    "ja": {
        "break a leg": "영어 관용구 — 일본 독자에게 생소",
        "눈치": "한국 문화 개념 — '空気を読む'로 대체 가능",
    },
}

# 문화권별 금기 주제
_CULTURE_TABOOS = {
    "ko": ["정치적 편향", "종교 비하"],
    "en": ["인종 차별", "성별 차별"],
    "ja": ["전쟁 미화", "정치적 편향"],
    "cn": ["정치적 민감 주제", "종교 비하"],
}


def check_idioms(content: str, target_culture: str) -> list:
    """문화권별 관용구 호환성 검사"""
    issues = []
    idioms = _CULTURE_IDIOMS.get(target_culture, {})

    content_lower = content.lower()

    for idiom, description in idioms.items():
        if idiom.lower() in content_lower:
            issues.append(CulturalIssue(
                issue_type="idiom",
                description=f"관용구 '{idiom}' 감지: {description}",
                suggestion=f"대상 문화({target_culture})에 맞는 표현으로 대체를 검토하세요",
                target_culture=target_culture,
            ))

    return issues


def check_date_format(content: str, target_culture: str) -> list:
    """
    날짜 형식 검사.

    MM/DD (미국식) vs DD/MM (유럽식) vs YYYY년 MM월 DD일 (한국식) 등.
    """
    issues = []

    # MM/DD/YYYY 패턴 (미국식)
    us_date = re.findall(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', content)
    # DD.MM.YYYY 패턴 (유럽식)
    eu_date = re.findall(r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', content)

    if target_culture == "ko":
        if us_date:
            issues.append(CulturalIssue(
                issue_type="format",
                description="미국식 날짜 형식(MM/DD/YYYY) 감지",
                suggestion="한국식 'YYYY년 MM월 DD일' 또는 'YYYY-MM-DD' 형식을 사용하세요",
                target_culture=target_culture,
            ))
        if eu_date:
            issues.append(CulturalIssue(
                issue_type="format",
                description="유럽식 날짜 형식(DD.MM.YYYY) 감지",
                suggestion="한국식 'YYYY년 MM월 DD일' 또는 'YYYY-MM-DD' 형식을 사용하세요",
                target_culture=target_culture,
            ))

    elif target_culture == "en":
        if eu_date:
            issues.append(CulturalIssue(
                issue_type="format",
                description="유럽식 날짜 형식(DD.MM.YYYY) 감지 — 미국 독자 혼란 가능",
                suggestion="MM/DD/YYYY 또는 Month DD, YYYY 형식을 사용하세요",
                target_culture=target_culture,
            ))

    elif target_culture == "ja":
        if us_date:
            issues.append(CulturalIssue(
                issue_type="format",
                description="미국식 날짜 형식(MM/DD/YYYY) 감지",
                suggestion="일본식 'YYYY年MM月DD日' 형식을 사용하세요",
                target_culture=target_culture,
            ))

    return issues


def check_taboo_topics(content: str, target_culture: str) -> list:
    """금기 주제 탐지"""
    issues = []
    taboos = _CULTURE_TABOOS.get(target_culture, [])

    for taboo in taboos:
        if taboo in content:
            issues.append(CulturalIssue(
                issue_type="taboo",
                description=f"민감 주제 '{taboo}' 감지",
                suggestion=f"대상 문화({target_culture})에서 민감할 수 있는 주제입니다. 중립적 표현으로 수정을 검토하세요.",
                target_culture=target_culture,
            ))

    return issues


def assess_fitness(content: str, target_culture: str) -> CulturalReport:
    """종합 문화 적합성 평가"""
    all_issues = []

    all_issues.extend(check_idioms(content, target_culture))
    all_issues.extend(check_date_format(content, target_culture))
    all_issues.extend(check_taboo_topics(content, target_culture))

    # 적합성 점수: 이슈 수에 따라 차감
    # 최소 0.0, 이슈 하나당 -0.15
    penalty = len(all_issues) * 0.15
    fitness_score = max(0.0, 1.0 - penalty)

    return CulturalReport(
        content_id=str(uuid.uuid4()),
        target_culture=target_culture,
        issues=all_issues,
        fitness_score=round(fitness_score, 4),
    )
