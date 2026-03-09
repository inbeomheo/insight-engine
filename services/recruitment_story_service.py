"""채용 스토리 패키지 서비스 — 기업 콘텐츠에서 EVP(Employee Value Proposition) 추출"""
import re
from dataclasses import dataclass, field


@dataclass
class EVPPackage:
    """채용 스토리 패키지"""
    company_values: list  # list[str] — 핵심 기업 가치
    culture_highlights: list  # list[str] — 문화 하이라이트
    employee_stories: list  # list[str] — 직원 스토리 포인트
    job_appeal_points: list  # list[str] — 직무 매력 포인트


# 가치 관련 키워드 사전
_VALUE_KEYWORDS: dict[str, str] = {
    "혁신": "혁신과 창의성을 핵심 가치로 추구합니다",
    "innovation": "혁신과 창의성을 핵심 가치로 추구합니다",
    "성장": "구성원의 지속적인 성장을 지원합니다",
    "growth": "구성원의 지속적인 성장을 지원합니다",
    "협업": "팀 간 협업과 시너지를 중시합니다",
    "collaboration": "팀 간 협업과 시너지를 중시합니다",
    "신뢰": "상호 신뢰를 기반으로 한 조직 문화를 갖추고 있습니다",
    "trust": "상호 신뢰를 기반으로 한 조직 문화를 갖추고 있습니다",
    "도전": "새로운 도전을 두려워하지 않는 문화를 가지고 있습니다",
    "challenge": "새로운 도전을 두려워하지 않는 문화를 가지고 있습니다",
    "고객": "고객 중심 사고를 최우선 가치로 삼습니다",
    "customer": "고객 중심 사고를 최우선 가치로 삼습니다",
    "책임": "책임감과 오너십을 중요시합니다",
    "responsibility": "책임감과 오너십을 중요시합니다",
    "투명": "투명한 의사소통을 지향합니다",
    "transparency": "투명한 의사소통을 지향합니다",
}

# 문화 관련 키워드
_CULTURE_KEYWORDS: dict[str, str] = {
    "재택": "유연 근무(재택/하이브리드)를 지원합니다",
    "remote": "유연 근무(재택/하이브리드)를 지원합니다",
    "자율": "자율적인 근무 환경을 제공합니다",
    "유연": "유연한 근무 시간을 보장합니다",
    "flexible": "유연한 근무 시간을 보장합니다",
    "교육": "체계적인 교육 및 역량 개발 프로그램을 운영합니다",
    "learning": "체계적인 교육 및 역량 개발 프로그램을 운영합니다",
    "복지": "다양한 복리후생 제도를 갖추고 있습니다",
    "benefits": "다양한 복리후생 제도를 갖추고 있습니다",
    "워라밸": "워라밸(일과 생활의 균형)을 존중합니다",
    "work-life": "워라밸(일과 생활의 균형)을 존중합니다",
    "수평": "수평적인 조직 문화를 지향합니다",
    "flat": "수평적인 조직 문화를 지향합니다",
    "스톡옵션": "스톡옵션/성과 보상 제도를 운영합니다",
    "stock": "스톡옵션/성과 보상 제도를 운영합니다",
    "동아리": "사내 동아리 및 커뮤니티 활동을 지원합니다",
    "멘토": "멘토링 프로그램을 통해 성장을 돕습니다",
    "mentoring": "멘토링 프로그램을 통해 성장을 돕습니다",
}

# 직원 스토리 패턴
_STORY_PATTERNS = [
    re.compile(r'(?:저는|나는|제가)\s+(.{10,60})', re.UNICODE),
    re.compile(r'(?:입사\s*(?:후|하고|해서))\s*(.{10,60})', re.UNICODE),
    re.compile(r'(?:팀에서|부서에서|회사에서)\s+(.{10,60})', re.UNICODE),
    re.compile(r'(?:경험|경력|성장).*?(?:할 수 있|했습니다|하고 있)', re.UNICODE),
]

# 직무 매력 키워드
_JOB_APPEAL_KEYWORDS: dict[str, str] = {
    "최신 기술": "최신 기술 스택을 활용한 개발 환경",
    "대규모": "대규모 서비스/프로젝트 경험 기회",
    "글로벌": "글로벌 시장을 대상으로 한 서비스 운영",
    "global": "글로벌 시장을 대상으로 한 서비스 운영",
    "오픈소스": "오픈소스 기여 및 커뮤니티 활동 장려",
    "open source": "오픈소스 기여 및 커뮤니티 활동 장려",
    "리더": "리더십 성장 경로가 명확합니다",
    "leader": "리더십 성장 경로가 명확합니다",
    "자기주도": "자기주도적 업무 수행이 가능합니다",
    "임팩트": "실질적인 사회적/비즈니스 임팩트를 만들 수 있습니다",
    "impact": "실질적인 사회적/비즈니스 임팩트를 만들 수 있습니다",
    "성과": "성과 기반 보상 체계를 운영합니다",
    "커리어": "체계적인 커리어 성장 경로를 제공합니다",
    "career": "체계적인 커리어 성장 경로를 제공합니다",
}


def _extract_by_keywords(content: str, keyword_map: dict[str, str]) -> list[str]:
    """콘텐츠에서 키워드 매칭으로 항목을 추출한다."""
    content_lower = content.lower()
    found = []
    seen_values = set()

    for keyword, description in keyword_map.items():
        if keyword.lower() in content_lower and description not in seen_values:
            found.append(description)
            seen_values.add(description)

    return found


def _extract_employee_stories(content: str) -> list[str]:
    """콘텐츠에서 직원 스토리 요소를 추출한다."""
    stories = []
    sentences = re.split(r'[.!?。\n]', content)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 15:
            continue

        for pattern in _STORY_PATTERNS:
            match = pattern.search(sentence)
            if match:
                story = sentence
                if len(story) > 80:
                    story = story[:77] + "..."
                if story not in stories:
                    stories.append(story)
                break

    # 스토리를 못 찾으면 1인칭 문장 탐색
    if not stories:
        for sentence in sentences:
            sentence = sentence.strip()
            if any(marker in sentence for marker in ["저는", "나는", "우리", "팀원"]):
                if len(sentence) >= 15:
                    story = sentence if len(sentence) <= 80 else sentence[:77] + "..."
                    stories.append(story)
                    if len(stories) >= 3:
                        break

    return stories[:5]


def package_evp(company_content: str) -> EVPPackage:
    """기업 콘텐츠에서 EVP 패키지를 구성한다.

    Args:
        company_content: 기업 소개/채용 관련 텍스트

    Returns:
        EVPPackage 구조
    """
    if not company_content or not company_content.strip():
        return EVPPackage(
            company_values=[],
            culture_highlights=[],
            employee_stories=[],
            job_appeal_points=[],
        )

    company_values = _extract_by_keywords(company_content, _VALUE_KEYWORDS)
    culture_highlights = _extract_by_keywords(company_content, _CULTURE_KEYWORDS)
    employee_stories = _extract_employee_stories(company_content)
    job_appeal_points = _extract_by_keywords(company_content, _JOB_APPEAL_KEYWORDS)

    return EVPPackage(
        company_values=company_values,
        culture_highlights=culture_highlights,
        employee_stories=employee_stories,
        job_appeal_points=job_appeal_points,
    )
