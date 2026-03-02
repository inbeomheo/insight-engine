"""
GEO 메타데이터 강화 통합 테스트 (Feature 33)

검증 항목:
- seo_metadata_service: JSON-LD 스키마 생성
- ai_service: extract_faq_schema, extract_cta
- generation_helpers: json_ld_schemas 응답 포함 (라우트 수준은 smoke 테스트)
"""
import json
import unittest


class TestSeoMetadataService(unittest.TestCase):
    """seo_metadata_service.py — JSON-LD 스키마 생성 유틸 테스트"""

    def test_generate_video_object_schema_basic(self):
        """VideoObject 스키마 필수 필드 포함 확인"""
        from services.seo_metadata_service import generate_video_object_schema

        schema = generate_video_object_schema(
            video_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='테스트 영상',
            description='테스트 설명',
        )

        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'VideoObject')
        self.assertEqual(schema['name'], '테스트 영상')
        self.assertIn('dQw4w9WgXcQ', schema['contentUrl'])
        self.assertIn('dQw4w9WgXcQ', schema['thumbnailUrl'])
        self.assertIn('description', schema)

    def test_generate_video_object_schema_no_url(self):
        """URL 없을 때 썸네일 없이 반환"""
        from services.seo_metadata_service import generate_video_object_schema

        schema = generate_video_object_schema(
            video_url='',
            title='제목만',
        )

        self.assertEqual(schema['@type'], 'VideoObject')
        self.assertNotIn('thumbnailUrl', schema)

    def test_generate_faq_page_schema_basic(self):
        """FAQPage 스키마 mainEntity 구조 확인"""
        from services.seo_metadata_service import generate_faq_page_schema

        faq_pairs = [
            {'question': 'RAG란 무엇인가?', 'answer': 'RAG는 검색 증강 생성 기술이다.'},
            {'question': 'RAG의 장점은?', 'answer': '환각을 줄이고 최신 정보를 반영한다.'},
        ]
        schema = generate_faq_page_schema(faq_pairs)

        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'FAQPage')
        self.assertEqual(len(schema['mainEntity']), 2)

        first = schema['mainEntity'][0]
        self.assertEqual(first['@type'], 'Question')
        self.assertEqual(first['name'], 'RAG란 무엇인가?')
        self.assertEqual(first['acceptedAnswer']['@type'], 'Answer')
        self.assertEqual(first['acceptedAnswer']['text'], 'RAG는 검색 증강 생성 기술이다.')

    def test_generate_faq_page_schema_empty(self):
        """빈 FAQ 리스트 처리"""
        from services.seo_metadata_service import generate_faq_page_schema

        schema = generate_faq_page_schema([])

        self.assertEqual(schema['@type'], 'FAQPage')
        self.assertEqual(schema['mainEntity'], [])

    def test_generate_faq_page_schema_skips_incomplete(self):
        """질문 또는 답변이 빈 항목은 건너뜀"""
        from services.seo_metadata_service import generate_faq_page_schema

        faq_pairs = [
            {'question': '완전한 Q', 'answer': '완전한 A'},
            {'question': '', 'answer': '답변만'},
            {'question': '질문만', 'answer': ''},
        ]
        schema = generate_faq_page_schema(faq_pairs)
        self.assertEqual(len(schema['mainEntity']), 1)

    def test_generate_article_schema_basic(self):
        """Article 스키마 기본 필드 확인"""
        from services.seo_metadata_service import generate_article_schema

        schema = generate_article_schema(
            title='AI 검색 최적화 완벽 가이드',
            description='GEO 기반 콘텐츠 작성법',
            keywords=['AI', 'SEO', 'GEO'],
        )

        self.assertEqual(schema['@context'], 'https://schema.org')
        self.assertEqual(schema['@type'], 'Article')
        self.assertIn('AI 검색 최적화', schema['headline'])
        self.assertEqual(schema['keywords'], ['AI', 'SEO', 'GEO'])

    def test_generate_article_schema_headline_truncated(self):
        """제목이 110자를 초과하면 잘림"""
        from services.seo_metadata_service import generate_article_schema

        long_title = 'A' * 200
        schema = generate_article_schema(title=long_title)
        self.assertLessEqual(len(schema['headline']), 110)

    def test_generate_all_schemas_returns_list(self):
        """generate_all_schemas가 리스트를 반환하고 VideoObject + Article 포함"""
        from services.seo_metadata_service import generate_all_schemas

        schemas = generate_all_schemas(
            video_url='https://www.youtube.com/watch?v=abc123abc12',
            title='테스트 제목',
            content='첫 번째 비빈 줄입니다. 설명에 사용됩니다.',
            faq_pairs=[],
            keywords=['키워드1'],
        )

        self.assertIsInstance(schemas, list)
        self.assertGreater(len(schemas), 0)

        types = [s['@type'] for s in schemas]
        self.assertIn('VideoObject', types)
        self.assertIn('Article', types)

    def test_generate_all_schemas_includes_faq_when_present(self):
        """FAQ 쌍이 있으면 FAQPage 스키마 포함"""
        from services.seo_metadata_service import generate_all_schemas

        faq_pairs = [
            {'question': 'Q1?', 'answer': 'A1.'},
        ]
        schemas = generate_all_schemas(
            video_url='https://youtu.be/dQw4w9WgXcQ',
            title='제목',
            content='본문',
            faq_pairs=faq_pairs,
        )

        types = [s['@type'] for s in schemas]
        self.assertIn('FAQPage', types)

    def test_generate_all_schemas_no_faq_when_empty(self):
        """FAQ가 없으면 FAQPage 스키마 미포함"""
        from services.seo_metadata_service import generate_all_schemas

        schemas = generate_all_schemas(
            video_url='https://youtu.be/dQw4w9WgXcQ',
            title='제목',
            content='본문',
            faq_pairs=[],
        )

        types = [s['@type'] for s in schemas]
        self.assertNotIn('FAQPage', types)

    def test_generate_all_schemas_valid_json(self):
        """생성된 스키마가 JSON 직렬화 가능 확인"""
        from services.seo_metadata_service import generate_all_schemas

        schemas = generate_all_schemas(
            video_url='https://www.youtube.com/watch?v=abc123abc12',
            title='JSON 직렬화 테스트',
            content='테스트 본문입니다.',
            faq_pairs=[{'question': 'Q?', 'answer': 'A.'}],
            keywords=['k1', 'k2'],
        )

        # JSON 직렬화 가능해야 함
        serialized = json.dumps(schemas)
        self.assertIsInstance(serialized, str)
        restored = json.loads(serialized)
        self.assertEqual(len(restored), len(schemas))


class TestExtractFaqSchema(unittest.TestCase):
    """ai_service.extract_faq_schema() 테스트"""

    def test_extracts_geo_seo_format(self):
        """geo_seo 형식의 **Q. ?** / A. 패턴 파싱"""
        from services.ai_service import extract_faq_schema

        content = """### 자주 묻는 질문

**Q. RAG란 무엇인가?**
A. RAG는 검색 증강 생성 기술로, 외부 문서를 검색하여 AI 답변의 정확도를 높입니다.

**Q. RAG의 장점은?**
A. 환각을 줄이고 최신 정보를 반영할 수 있으며 도메인 특화 답변이 가능합니다.

**Q. RAG를 적용하려면?**
A. 벡터 DB와 임베딩 모델이 필요합니다.
"""
        result = extract_faq_schema(content)
        self.assertIsNotNone(result)
        self.assertEqual(result['@type'], 'FAQPage')
        self.assertGreaterEqual(len(result['mainEntity']), 2)

        first = result['mainEntity'][0]
        self.assertEqual(first['@type'], 'Question')
        self.assertIn('RAG', first['name'])

    def test_returns_none_when_no_qa(self):
        """Q&A 패턴이 없으면 None 반환"""
        from services.ai_service import extract_faq_schema

        content = "일반 텍스트입니다. Q&A 형식이 아닙니다."
        result = extract_faq_schema(content)
        self.assertIsNone(result)

    def test_returns_none_for_empty(self):
        """빈 콘텐츠에 대해 None 반환"""
        from services.ai_service import extract_faq_schema

        self.assertIsNone(extract_faq_schema(''))
        self.assertIsNone(extract_faq_schema(None))

    def test_schema_is_json_serializable(self):
        """추출된 스키마가 JSON 직렬화 가능 확인"""
        from services.ai_service import extract_faq_schema

        content = """**Q. 테스트 질문?**
A. 테스트 답변입니다. 정확한 답변을 제공합니다.

**Q. 두 번째 질문?**
A. 두 번째 답변입니다.
"""
        result = extract_faq_schema(content)
        if result:
            serialized = json.dumps(result)
            self.assertIsInstance(serialized, str)


class TestExtractCta(unittest.TestCase):
    """ai_service.extract_cta() 테스트"""

    def test_extracts_primary_and_secondary(self):
        """CTA_PRIMARY, CTA_SECONDARY 모두 추출"""
        from services.ai_service import extract_cta

        content = """### CTA (Call-to-Action)

**CTA_PRIMARY**: 공식 문서에서 더 알아보기
**CTA_SECONDARY**: 튜토리얼 영상 시청하기
"""
        result = extract_cta(content)
        self.assertIsNotNone(result)
        self.assertEqual(result['primary'], '공식 문서에서 더 알아보기')
        self.assertEqual(result['secondary'], '튜토리얼 영상 시청하기')

    def test_extracts_primary_only(self):
        """CTA_PRIMARY만 있을 때"""
        from services.ai_service import extract_cta

        content = "**CTA_PRIMARY**: GitHub 저장소 방문하기"
        result = extract_cta(content)
        self.assertIsNotNone(result)
        self.assertIn('primary', result)
        self.assertNotIn('secondary', result)

    def test_returns_none_when_no_cta(self):
        """CTA 패턴이 없으면 None 반환"""
        from services.ai_service import extract_cta

        content = "CTA가 없는 일반 텍스트입니다."
        result = extract_cta(content)
        self.assertIsNone(result)

    def test_returns_none_for_empty(self):
        """빈 콘텐츠에 대해 None 반환"""
        from services.ai_service import extract_cta

        self.assertIsNone(extract_cta(''))
        self.assertIsNone(extract_cta(None))


class TestJsonLdSchemaIntegration(unittest.TestCase):
    """JSON-LD 스키마 생성 + FAQ 추출 통합 테스트"""

    def test_full_geo_seo_flow(self):
        """geo_seo 스타일 콘텐츠에서 FAQ → JSON-LD 스키마 전체 흐름 검증"""
        from services.ai_service import extract_faq_schema
        from services.seo_metadata_service import generate_all_schemas

        geo_content = """# RAG: AI 답변 정확도를 높이는 검색 증강 생성

### 한 줄 정의
> RAG는 외부 문서 검색과 AI 생성을 결합하여 환각을 줄이는 기술이다.

### 자주 묻는 질문 (FAQ)

**Q. RAG란 무엇인가?**
A. RAG(Retrieval-Augmented Generation)는 AI가 답변 생성 전 외부 문서를 검색하는 기술이다.

**Q. RAG가 필요한 이유는?**
A. 대형 언어 모델의 환각 현상을 줄이고 최신 정보를 반영하기 위해 필요하다.

### 엔티티 태그
`RAG` `LLM` `벡터 DB` `임베딩`

**CTA_PRIMARY**: RAG 튜토리얼 따라하기
"""
        # FAQ 스키마 추출
        faq_schema = extract_faq_schema(geo_content)
        self.assertIsNotNone(faq_schema)
        faq_pairs = [
            {
                'question': e['name'],
                'answer': e['acceptedAnswer']['text']
            }
            for e in faq_schema['mainEntity']
        ]

        # 전체 JSON-LD 스키마 생성
        schemas = generate_all_schemas(
            video_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            title='RAG: AI 답변 정확도를 높이는 검색 증강 생성',
            content=geo_content,
            faq_pairs=faq_pairs,
            keywords=['RAG', 'LLM', '벡터 DB'],
        )

        types = [s['@type'] for s in schemas]
        self.assertIn('VideoObject', types)
        self.assertIn('FAQPage', types)
        self.assertIn('Article', types)

        # JSON 직렬화 확인
        serialized = json.dumps(schemas, ensure_ascii=False)
        self.assertIn('RAG', serialized)

    def test_video_id_extraction_various_urls(self):
        """다양한 YouTube URL 형식에서 video_id 추출"""
        from services.seo_metadata_service import generate_video_object_schema

        test_cases = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/embed/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
            ('https://www.youtube.com/shorts/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ]

        for url, expected_id in test_cases:
            schema = generate_video_object_schema(url, '제목')
            self.assertIn(expected_id, schema['thumbnailUrl'], f"Failed for: {url}")
            self.assertIn(expected_id, schema['contentUrl'], f"Failed for: {url}")


if __name__ == '__main__':
    unittest.main()
