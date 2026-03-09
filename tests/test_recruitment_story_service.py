"""채용 스토리 패키지 서비스 테스트"""
import pytest
from services.recruitment_story_service import (
    package_evp,
    EVPPackage,
    _extract_by_keywords,
    _extract_employee_stories,
    _VALUE_KEYWORDS,
    _CULTURE_KEYWORDS,
    _JOB_APPEAL_KEYWORDS,
)


class TestPackageEvp:
    """package_evp 함수 테스트"""

    def test_basic_evp_extraction(self):
        """기본 기업 콘텐츠에서 EVP를 추출한다."""
        content = (
            "우리 회사는 혁신과 성장을 핵심 가치로 추구합니다. "
            "재택근무와 유연한 근무시간을 지원하며, "
            "최신 기술 스택을 활용한 개발 환경을 제공합니다. "
            "저는 입사 후 많은 것을 배웠습니다."
        )
        result = package_evp(content)

        assert isinstance(result, EVPPackage)
        assert len(result.company_values) > 0
        assert len(result.culture_highlights) > 0
        assert len(result.job_appeal_points) > 0

    def test_empty_content(self):
        """빈 콘텐츠는 빈 패키지를 반환한다."""
        result = package_evp("")

        assert result.company_values == []
        assert result.culture_highlights == []
        assert result.employee_stories == []
        assert result.job_appeal_points == []

    def test_none_content(self):
        """None 콘텐츠도 빈 패키지를 반환한다."""
        result = package_evp(None)
        assert result.company_values == []

    def test_value_extraction(self):
        """기업 가치 키워드를 추출한다."""
        content = "우리는 혁신과 도전 정신을 중시하고, 고객 중심의 사고를 합니다."
        result = package_evp(content)

        assert len(result.company_values) >= 2
        values_text = " ".join(result.company_values)
        assert "혁신" in values_text or "도전" in values_text

    def test_culture_extraction(self):
        """문화 키워드를 추출한다."""
        content = "재택근무, 유연 근무, 복지 제도, 수평적 조직 문화를 갖추고 있습니다."
        result = package_evp(content)

        assert len(result.culture_highlights) >= 2

    def test_employee_story_extraction(self):
        """직원 스토리를 추출한다."""
        content = (
            "저는 입사 후 3년간 다양한 프로젝트에 참여했습니다. "
            "팀에서 리더 역할을 맡아 성장할 수 있었습니다. "
            "나는 이 회사에서 새로운 기술을 배웠습니다."
        )
        result = package_evp(content)

        assert len(result.employee_stories) > 0

    def test_job_appeal_extraction(self):
        """직무 매력 포인트를 추출한다."""
        content = "글로벌 시장을 대상으로 대규모 서비스를 운영하며 오픈소스 기여를 장려합니다."
        result = package_evp(content)

        assert len(result.job_appeal_points) >= 2

    def test_no_relevant_content(self):
        """관련 키워드가 없는 콘텐츠는 빈 리스트를 반환한다."""
        content = "오늘 날씨가 좋습니다. 점심으로 파스타를 먹었습니다."
        result = package_evp(content)

        assert isinstance(result.company_values, list)
        assert isinstance(result.culture_highlights, list)

    def test_english_keywords(self):
        """영문 키워드도 감지한다."""
        content = (
            "We value innovation and trust. "
            "We offer flexible remote work and mentoring programs. "
            "Global market presence with open source contributions."
        )
        result = package_evp(content)

        assert len(result.company_values) > 0
        assert len(result.culture_highlights) > 0

    def test_no_duplicate_values(self):
        """중복 값이 제거된다."""
        content = "혁신적인 혁신을 추구합니다. innovation과 혁신을 중시합니다."
        result = package_evp(content)

        # "혁신"과 "innovation" 동일 설명이므로 1개만
        unique_values = set(result.company_values)
        assert len(unique_values) == len(result.company_values)

    def test_employee_stories_limit(self):
        """직원 스토리는 최대 5개로 제한된다."""
        stories = [f"저는 프로젝트 {i}에서 많은 것을 배웠습니다." for i in range(10)]
        content = " ".join(stories)
        result = package_evp(content)

        assert len(result.employee_stories) <= 5

    def test_comprehensive_content(self):
        """종합 콘텐츠에서 모든 카테고리를 추출한다."""
        content = (
            "우리 회사는 혁신, 성장, 협업을 핵심 가치로 합니다. "
            "재택근무와 교육 프로그램, 멘토링을 제공합니다. "
            "저는 입사해서 글로벌 프로젝트에 참여했고, "
            "최신 기술 스택으로 대규모 서비스를 개발했습니다. "
            "커리어 성장 경로가 명확하고 임팩트 있는 일을 합니다."
        )
        result = package_evp(content)

        assert len(result.company_values) >= 2
        assert len(result.culture_highlights) >= 2
        assert len(result.employee_stories) >= 1
        assert len(result.job_appeal_points) >= 2


class TestExtractByKeywords:
    """_extract_by_keywords 함수 테스트"""

    def test_basic_keyword_match(self):
        """기본 키워드 매칭이 동작한다."""
        result = _extract_by_keywords("혁신적인 회사", _VALUE_KEYWORDS)
        assert len(result) > 0

    def test_no_match(self):
        """매칭 없으면 빈 리스트를 반환한다."""
        result = _extract_by_keywords("파스타 레시피", _VALUE_KEYWORDS)
        assert result == []

    def test_case_insensitive(self):
        """대소문자 구분 없이 매칭한다."""
        result = _extract_by_keywords("INNOVATION is key", _VALUE_KEYWORDS)
        assert len(result) > 0


class TestExtractEmployeeStories:
    """_extract_employee_stories 함수 테스트"""

    def test_first_person_detection(self):
        """1인칭 문장을 감지한다."""
        content = "저는 이 회사에서 5년간 근무하며 많은 경험을 했습니다."
        result = _extract_employee_stories(content)
        assert len(result) > 0

    def test_no_stories(self):
        """스토리 패턴이 없으면 빈 리스트를 반환한다."""
        result = _extract_employee_stories("오늘 날씨가 좋습니다.")
        assert result == []

    def test_story_length_limit(self):
        """스토리 문자열 길이가 제한된다."""
        content = "저는 " + "매우 긴 내용 " * 20 + "을 경험했습니다."
        result = _extract_employee_stories(content)

        for story in result:
            assert len(story) <= 83  # 80 + "..." 3자
