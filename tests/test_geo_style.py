"""
GEO (Generative Engine Optimization) 스타일 통합 테스트
프롬프트 로드, 메타데이터 파싱, config 등록 검증
"""
import unittest


class TestGeoStyleRegistration(unittest.TestCase):
    """GEO 스타일이 config와 프롬프트에 올바르게 등록되었는지 확인"""

    def test_geo_seo_in_style_prompts(self):
        """STYLE_PROMPTS에 geo_seo가 포함되어 있는지 확인"""
        from prompts.styles import STYLE_PROMPTS
        self.assertIn('geo_seo', STYLE_PROMPTS)

    def test_geo_seo_prompt_not_empty(self):
        """GEO 프롬프트가 비어있지 않은지 확인"""
        from prompts.styles import STYLE_PROMPTS
        prompt = STYLE_PROMPTS['geo_seo']
        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 100)

    def test_geo_seo_in_style_options(self):
        """STYLE_OPTIONS에 geo_seo가 포함되어 있는지 확인"""
        import config
        style_keys = [k for k, _ in config.STYLE_OPTIONS]
        self.assertIn('geo_seo', style_keys)

    def test_geo_seo_temperature(self):
        """STYLE_TEMPERATURE에 geo_seo가 정밀형(0.5)으로 설정되었는지 확인"""
        import config
        self.assertIn('geo_seo', config.STYLE_TEMPERATURE)
        self.assertEqual(config.STYLE_TEMPERATURE['geo_seo'], 0.5)

    def test_geo_seo_style_label(self):
        """GEO 스타일 라벨이 올바른지 확인"""
        import config
        style_dict = dict(config.STYLE_OPTIONS)
        self.assertIn('GEO', style_dict['geo_seo'])


class TestExtractGeoMetadata(unittest.TestCase):
    """extract_geo_metadata() 파싱 테스트"""

    def test_extract_key_facts(self):
        """주요 팩트 추출 확인"""
        from services.ai_service import extract_geo_metadata

        content = """### 주요 팩트

- ✓ RAG는 검색과 생성을 결합한 기술이다
- ✓ 환각을 줄이는 데 효과적이다
- ✓ 2020년 Facebook AI Research에서 처음 제안되었다
"""
        result = extract_geo_metadata(content)
        self.assertIsNotNone(result)
        self.assertIn('key_facts', result)
        self.assertGreaterEqual(len(result['key_facts']), 2)

    def test_extract_structured_data(self):
        """구조화된 데이터 테이블 추출 확인"""
        from services.ai_service import extract_geo_metadata

        content = """### 구조화 데이터

| 항목 | 내용 |
|------|------|
| **핵심 개념** | 검색 증강 생성 |
| **관련 기술** | 벡터 DB, 임베딩 |
| **적용 분야** | 챗봇, QA 시스템 |
"""
        result = extract_geo_metadata(content)
        self.assertIsNotNone(result)
        self.assertIn('structured_data', result)
        self.assertIn('핵심 개념', result['structured_data'])
        self.assertEqual(result['structured_data']['핵심 개념'], '검색 증강 생성')

    def test_extract_entity_tags(self):
        """엔티티 태그 추출 확인"""
        from services.ai_service import extract_geo_metadata

        content = """### 엔티티 태그
`RAG` `LLM` `벡터 DB` `임베딩` `검색 증강 생성`
"""
        result = extract_geo_metadata(content)
        self.assertIsNotNone(result)
        self.assertIn('entity_tags', result)
        self.assertIn('RAG', result['entity_tags'])
        self.assertIn('LLM', result['entity_tags'])

    def test_extract_citations(self):
        """인용문 추출 확인 (한 줄 정의 + Q&A)"""
        from services.ai_service import extract_geo_metadata

        content = """### 한 줄 정의
> RAG는 외부 데이터를 검색하여 AI 답변의 정확도를 높이는 기술이다.

### 자주 묻는 질문

**Q. RAG란 무엇인가?**
A. RAG(Retrieval-Augmented Generation)는 대규모 언어 모델이 답변 생성 전에 외부 지식베이스를 검색하는 기술이다.

**Q. RAG의 장점은?**
A. 환각을 줄이고 최신 정보를 반영할 수 있으며 도메인 특화 답변이 가능하다.
"""
        result = extract_geo_metadata(content)
        self.assertIsNotNone(result)
        self.assertIn('citations', result)
        self.assertGreaterEqual(len(result['citations']), 2)

    def test_empty_content_returns_none(self):
        """빈 콘텐츠는 None 반환"""
        from services.ai_service import extract_geo_metadata

        self.assertIsNone(extract_geo_metadata(''))
        self.assertIsNone(extract_geo_metadata(None))

    def test_no_geo_sections_returns_none(self):
        """GEO 관련 섹션이 없으면 None 반환"""
        from services.ai_service import extract_geo_metadata

        content = "일반적인 블로그 글입니다. 특별한 구조 없이 작성되었습니다."
        self.assertIsNone(extract_geo_metadata(content))


if __name__ == "__main__":
    unittest.main()
