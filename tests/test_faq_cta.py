"""
FAQ JSON-LD 스키마 추출 및 CTA 추출 함수 통합 테스트

검증 기준:
- extract_faq_schema()가 올바른 JSON-LD FAQPage 스키마를 반환하는지
- extract_cta()가 CTA 문구를 올바르게 추출하는지
- 엣지 케이스(FAQ 없음, 부분 입력, None 입력) 처리 확인
"""
import pytest
from unittest.mock import patch


# Flask 앱 컨텍스트 없이 테스트하기 위한 임포트 패치
@pytest.fixture(autouse=True)
def patch_supabase():
    with patch('services.supabase_service.is_supabase_enabled', return_value=False):
        yield


# ── extract_faq_schema 테스트 ──────────────────────────────────

from services.ai_service import extract_faq_schema, extract_cta


SAMPLE_BLOG_SEO_CONTENT = """
### 도입
Python은 배우기 쉬운 프로그래밍 언어입니다.

---

### 자주 묻는 질문 (FAQ)

**Q. Python을 배우려면 얼마나 걸리나요?**
A. 기본 문법은 1~2개월이면 익힐 수 있습니다. 꾸준한 연습이 중요합니다.

**Q. Python으로 무엇을 만들 수 있나요?**
A. 웹 개발, 데이터 분석, AI/ML, 자동화 스크립트 등 다양한 분야에 활용할 수 있습니다.

**Q. Python과 JavaScript 중 어느 것을 먼저 배워야 하나요?**
A. 목적에 따라 다릅니다. 데이터 분석이나 AI 쪽이면 Python, 웹 프론트엔드면 JavaScript를 먼저 배우세요.

---

### 정리하며
Python은 입문자에게 좋은 언어입니다.
"""

SAMPLE_GEO_SEO_CONTENT = """
### 자주 묻는 질문 (FAQ)

**Q. RAG란 무엇인가요?**
A. RAG(Retrieval-Augmented Generation)는 외부 지식베이스를 검색하여 AI 응답의 정확도를 높이는 기술입니다.

**Q. RAG와 Fine-tuning의 차이는 무엇인가요?**
A. RAG는 실시간 검색으로 지식을 주입하고, Fine-tuning은 모델 자체를 재학습시킵니다.

---

### CTA (Call-to-Action)

**CTA_PRIMARY**: 공식 문서에서 RAG 구현 방법 알아보기
**CTA_SECONDARY**: 무료 튜토리얼 시작하기
"""

CONTENT_NO_FAQ = """
### 도입
이 글은 FAQ 섹션이 없는 예시입니다.

### 본문
내용이 여기 있습니다.
"""

CONTENT_PARTIAL_FAQ = """
**Q. 질문만 있고 답변이 없는 경우?**

다른 내용
"""


class TestExtractFaqSchema:
    def test_기본_faq_추출(self):
        """blog_seo 스타일의 Q&A에서 FAQPage 스키마가 생성되어야 합니다."""
        result = extract_faq_schema(SAMPLE_BLOG_SEO_CONTENT)

        assert result is not None
        assert result['@context'] == 'https://schema.org'
        assert result['@type'] == 'FAQPage'
        assert 'mainEntity' in result
        assert len(result['mainEntity']) == 3

    def test_faq_항목_구조(self):
        """각 FAQ 항목이 올바른 JSON-LD 구조를 가져야 합니다."""
        result = extract_faq_schema(SAMPLE_BLOG_SEO_CONTENT)
        item = result['mainEntity'][0]

        assert item['@type'] == 'Question'
        assert 'name' in item
        assert 'acceptedAnswer' in item
        assert item['acceptedAnswer']['@type'] == 'Answer'
        assert 'text' in item['acceptedAnswer']

    def test_faq_내용_정확성(self):
        """추출된 Q&A 내용이 원본과 일치해야 합니다."""
        result = extract_faq_schema(SAMPLE_BLOG_SEO_CONTENT)
        first = result['mainEntity'][0]

        assert 'Python을 배우려면 얼마나 걸리나요' in first['name']
        assert '1~2개월' in first['acceptedAnswer']['text']

    def test_geo_seo_faq_추출(self):
        """geo_seo 스타일의 Q&A에서도 FAQPage 스키마가 생성되어야 합니다."""
        result = extract_faq_schema(SAMPLE_GEO_SEO_CONTENT)

        assert result is not None
        assert len(result['mainEntity']) == 2

    def test_faq_없음_none_반환(self):
        """FAQ 섹션이 없으면 None을 반환해야 합니다."""
        result = extract_faq_schema(CONTENT_NO_FAQ)
        assert result is None

    def test_빈_문자열_none_반환(self):
        """빈 문자열 입력 시 None을 반환해야 합니다."""
        result = extract_faq_schema('')
        assert result is None

    def test_none_입력_none_반환(self):
        """None 입력 시 None을 반환해야 합니다."""
        result = extract_faq_schema(None)
        assert result is None

    def test_불완전한_qa_처리(self):
        """답변이 없는 불완전한 Q&A는 무시되어야 합니다."""
        result = extract_faq_schema(CONTENT_PARTIAL_FAQ)
        # 답변 없이 질문만 있으면 추출 불가 → None
        assert result is None


class TestExtractCta:
    def test_primary_cta_추출(self):
        """CTA_PRIMARY 문구가 정확하게 추출되어야 합니다."""
        result = extract_cta(SAMPLE_GEO_SEO_CONTENT)

        assert result is not None
        assert 'primary' in result
        assert result['primary'] == '공식 문서에서 RAG 구현 방법 알아보기'

    def test_secondary_cta_추출(self):
        """CTA_SECONDARY 문구가 정확하게 추출되어야 합니다."""
        result = extract_cta(SAMPLE_GEO_SEO_CONTENT)

        assert result is not None
        assert 'secondary' in result
        assert result['secondary'] == '무료 튜토리얼 시작하기'

    def test_cta_없음_none_반환(self):
        """CTA 섹션이 없으면 None을 반환해야 합니다."""
        result = extract_cta(SAMPLE_BLOG_SEO_CONTENT)
        assert result is None

    def test_primary_만_있는_경우(self):
        """PRIMARY만 있을 때 secondary 없이 반환해야 합니다."""
        content = "**CTA_PRIMARY**: 지금 시작하기"
        result = extract_cta(content)

        assert result is not None
        assert result['primary'] == '지금 시작하기'
        assert 'secondary' not in result or result.get('secondary') is None

    def test_빈_문자열_none_반환(self):
        """빈 문자열 입력 시 None을 반환해야 합니다."""
        result = extract_cta('')
        assert result is None

    def test_none_입력_none_반환(self):
        """None 입력 시 None을 반환해야 합니다."""
        result = extract_cta(None)
        assert result is None


class TestFaqCtaIntegration:
    def test_blog_seo_faq_있고_cta_없음(self):
        """blog_seo 콘텐츠에는 FAQ가 있고 CTA는 없어야 합니다."""
        faq = extract_faq_schema(SAMPLE_BLOG_SEO_CONTENT)
        cta = extract_cta(SAMPLE_BLOG_SEO_CONTENT)

        assert faq is not None
        assert cta is None

    def test_geo_seo_faq_cta_모두_있음(self):
        """geo_seo 콘텐츠에는 FAQ와 CTA 모두 추출되어야 합니다."""
        faq = extract_faq_schema(SAMPLE_GEO_SEO_CONTENT)
        cta = extract_cta(SAMPLE_GEO_SEO_CONTENT)

        assert faq is not None
        assert cta is not None

    def test_faq_schema_직렬화_가능(self):
        """추출된 FAQ 스키마가 JSON으로 직렬화 가능해야 합니다."""
        import json
        faq = extract_faq_schema(SAMPLE_BLOG_SEO_CONTENT)

        assert faq is not None
        json_str = json.dumps(faq, ensure_ascii=False)
        restored = json.loads(json_str)
        assert restored['@type'] == 'FAQPage'
        assert len(restored['mainEntity']) == 3
