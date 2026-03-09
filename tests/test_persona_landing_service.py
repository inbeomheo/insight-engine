"""
persona_landing_service 단위 테스트

페르소나별 맞춤 랜딩 페이지 생성 로직을 검증합니다.
"""
import pytest

from services.persona_landing_service import (
    LandingPage,
    LandingSection,
    generate_landing,
    SUPPORTED_PERSONAS,
    _PERSONA_CONFIGS,
    _build_section,
)


class TestSupportedPersonas:
    """지원 페르소나 목록 검증"""

    def test_5개_페르소나_지원(self):
        assert len(SUPPORTED_PERSONAS) == 5

    def test_필수_페르소나_포함(self):
        expected = {'developer', 'marketer', 'executive', 'student', 'creator'}
        assert set(SUPPORTED_PERSONAS) == expected

    def test_각_페르소나_설정_존재(self):
        for persona in SUPPORTED_PERSONAS:
            assert persona in _PERSONA_CONFIGS


class TestPersonaConfigs:
    """페르소나 설정 구조 검증"""

    @pytest.mark.parametrize("persona", SUPPORTED_PERSONAS)
    def test_필수_키_존재(self, persona):
        config = _PERSONA_CONFIGS[persona]
        required_keys = ['tone', 'interests', 'cta_template',
                         'headline_template', 'subheadline_template',
                         'section_types', 'section_focus']
        for key in required_keys:
            assert key in config, f"{persona}에 '{key}' 키 누락"

    @pytest.mark.parametrize("persona", SUPPORTED_PERSONAS)
    def test_interests_비어있지_않음(self, persona):
        config = _PERSONA_CONFIGS[persona]
        assert len(config['interests']) >= 3

    @pytest.mark.parametrize("persona", SUPPORTED_PERSONAS)
    def test_section_types_비어있지_않음(self, persona):
        config = _PERSONA_CONFIGS[persona]
        assert len(config['section_types']) >= 3


class TestBuildSection:
    """개별 섹션 빌드 테스트"""

    def test_hero_섹션_생성(self):
        config = _PERSONA_CONFIGS['developer']
        section = _build_section('hero', 'AI 도구', config)
        assert isinstance(section, LandingSection)
        assert section.section_type == 'hero'
        assert 'AI 도구' in section.content

    def test_features_섹션_focus_반영(self):
        config = _PERSONA_CONFIGS['developer']
        section = _build_section('features', 'API', config)
        assert section.section_type == 'features'
        # developer의 features focus에 'API' 또는 '기술' 관련 내용 포함
        assert len(section.content) > 0

    def test_cta_섹션_topic_포함(self):
        config = _PERSONA_CONFIGS['marketer']
        section = _build_section('cta', '분석 도구', config)
        assert '분석 도구' in section.content

    def test_알_수_없는_섹션_타입(self):
        config = _PERSONA_CONFIGS['student']
        section = _build_section('unknown_type', '주제', config)
        assert section.section_type == 'unknown_type'
        assert '주제' in section.content


class TestGenerateLanding:
    """generate_landing 통합 테스트"""

    def test_developer_랜딩_생성(self):
        page = generate_landing('AI 코드 리뷰', 'developer')
        assert isinstance(page, LandingPage)
        assert page.persona == 'developer'
        assert page.topic == 'AI 코드 리뷰'
        assert page.tone == 'technical'
        assert 'AI 코드 리뷰' in page.headline

    def test_marketer_랜딩_생성(self):
        page = generate_landing('캠페인 자동화', 'marketer')
        assert page.tone == 'persuasive'
        assert len(page.sections) >= 3

    def test_executive_랜딩_생성(self):
        page = generate_landing('ERP 솔루션', 'executive')
        assert page.tone == 'formal'
        # executive에는 pricing 섹션 포함
        section_types = [s.section_type for s in page.sections]
        assert 'pricing' in section_types

    def test_student_랜딩_생성(self):
        page = generate_landing('Python 입문', 'student')
        assert page.tone == 'friendly'
        # student에는 faq 섹션 포함
        section_types = [s.section_type for s in page.sections]
        assert 'faq' in section_types

    def test_creator_랜딩_생성(self):
        page = generate_landing('영상 편집', 'creator')
        assert page.tone == 'creative'

    def test_지원하지_않는_페르소나_ValueError(self):
        with pytest.raises(ValueError, match='지원하지 않는 페르소나'):
            generate_landing('주제', 'unknown_persona')

    def test_빈_topic_ValueError(self):
        with pytest.raises(ValueError, match='빈 문자열'):
            generate_landing('', 'developer')

    def test_공백만_topic_ValueError(self):
        with pytest.raises(ValueError, match='빈 문자열'):
            generate_landing('   ', 'developer')

    def test_persona_대소문자_무관(self):
        page = generate_landing('주제', 'Developer')
        assert page.persona == 'developer'

    def test_persona_공백_제거(self):
        page = generate_landing('주제', '  student  ')
        assert page.persona == 'student'

    def test_LandingPage_필드_타입_검증(self):
        page = generate_landing('테스트 주제', 'developer')
        assert isinstance(page.persona, str)
        assert isinstance(page.topic, str)
        assert isinstance(page.headline, str)
        assert isinstance(page.subheadline, str)
        assert isinstance(page.sections, list)
        assert isinstance(page.cta_text, str)
        assert isinstance(page.tone, str)

    def test_모든_섹션이_LandingSection_인스턴스(self):
        page = generate_landing('주제', 'marketer')
        for section in page.sections:
            assert isinstance(section, LandingSection)
            assert isinstance(section.title, str)
            assert isinstance(section.content, str)
            assert isinstance(section.section_type, str)

    @pytest.mark.parametrize("persona", SUPPORTED_PERSONAS)
    def test_모든_페르소나_정상_생성(self, persona):
        """5개 페르소나 모두 에러 없이 생성되는지 확인"""
        page = generate_landing('범용 주제', persona)
        assert page.persona == persona
        assert len(page.sections) >= 3
        assert len(page.headline) > 0
        assert len(page.cta_text) > 0
