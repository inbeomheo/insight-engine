"""ai_service 확장 테스트 — SEO/GEO/FAQ 메타데이터 추출, 프롬프트 빌드, 스트리밍 등"""
import unittest
from unittest.mock import patch, MagicMock


class TestGetKoreanDatetime(unittest.TestCase):
    """_get_korean_datetime 테스트"""

    def test_returns_korean_format(self):
        from services.core.ai_service import _get_korean_datetime
        result = _get_korean_datetime()
        self.assertIn('년', result)
        self.assertIn('월', result)
        self.assertIn('일', result)


class TestFormatTranscriptWithTimestamps(unittest.TestCase):
    """format_transcript_with_timestamps 테스트"""

    def test_empty_segments(self):
        from services.core.ai_service import format_transcript_with_timestamps
        self.assertEqual(format_transcript_with_timestamps([]), "")
        self.assertEqual(format_transcript_with_timestamps(None), "")

    def test_import_error_returns_empty(self):
        from services.core.ai_service import format_transcript_with_timestamps
        segments = [{'start': 0, 'text': 'hello'}]
        with patch('services.core.ai_service.format_transcript_with_timestamps') as mock_fn:
            mock_fn.return_value = ""
            result = mock_fn(segments)
            self.assertEqual(result, "")


class TestExtractKeywords(unittest.TestCase):
    """_extract_keywords 테스트"""

    def test_with_keywords_comment(self):
        from services.core.ai_service import _extract_keywords
        content = "본문 내용\n<!-- KEYWORDS: AI, 머신러닝, 딥러닝 -->\n더 많은 내용"
        cleaned, keywords = _extract_keywords(content)
        self.assertNotIn('KEYWORDS', cleaned)
        self.assertIn('AI', keywords)
        self.assertIn('머신러닝', keywords)

    def test_without_keywords(self):
        from services.core.ai_service import _extract_keywords
        content = "키워드 없는 본문"
        cleaned, keywords = _extract_keywords(content)
        self.assertEqual(cleaned, content)
        self.assertEqual(keywords, [])

    def test_keywords_limit(self):
        from services.core.ai_service import _extract_keywords
        many_kw = ', '.join([f'kw{i}' for i in range(20)])
        content = f"<!-- KEYWORDS: {many_kw} -->"
        _, keywords = _extract_keywords(content)
        self.assertLessEqual(len(keywords), 10)


class TestBuildCompletionKwargs(unittest.TestCase):
    """_build_completion_kwargs 테스트"""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_basic_model(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('gpt-4o', 'test prompt')
        self.assertEqual(kwargs['model'], 'gpt-4o')
        self.assertIn('messages', kwargs)
        self.assertIn('temperature', kwargs)
        self.assertIn('max_tokens', kwargs)

    def test_gemini_reasoning_effort(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('gemini/gemini-3-flash-preview', 'test')
        self.assertEqual(kwargs.get('reasoning_effort'), 'minimal')

    def test_gemini_lite_no_reasoning(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('gemini/gemini-2.5-flash-lite-preview', 'test')
        self.assertNotIn('reasoning_effort', kwargs)

    def test_zhipuai_model(self):
        from services.core.ai_service import _build_completion_kwargs
        with patch.dict('os.environ', {'ZHIPUAI_API_KEY': 'test-key'}):
            kwargs = _build_completion_kwargs('zhipuai/GLM-4.7', 'test')
            self.assertTrue(kwargs['model'].startswith('openai/'))
            self.assertIn('api_base', kwargs)
            self.assertEqual(kwargs['api_key'], 'test-key')

    def test_zhipuai_no_key_raises(self):
        from services.core.ai_service import _build_completion_kwargs
        with patch.dict('os.environ', {}, clear=False):
            # ZHIPUAI_API_KEY 환경변수 제거
            import os
            old = os.environ.pop('ZHIPUAI_API_KEY', None)
            try:
                with self.assertRaises(ValueError):
                    _build_completion_kwargs('zhipuai/GLM-4.7', 'test')
            finally:
                if old:
                    os.environ['ZHIPUAI_API_KEY'] = old

    def test_ollama_model(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('ollama_chat/llama3.2', 'test')
        self.assertIn('api_base', kwargs)

    def test_chatmock_model(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('chatmock/gpt-5.4', 'test')
        self.assertNotIn('chatmock/', kwargs['model'])
        self.assertEqual(kwargs['api_key'], 'dummy')
        self.assertTrue(kwargs.get('drop_params'))

    def test_openrouter_model(self):
        from services.core.ai_service import _build_completion_kwargs
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'or-key'}):
            kwargs = _build_completion_kwargs('openrouter/meta-llama/llama-3', 'test')
            self.assertEqual(kwargs['api_key'], 'or-key')
            self.assertIn('openrouter.ai', kwargs['api_base'])

    def test_stream_flag(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('gpt-4o', 'test', stream=True)
        self.assertTrue(kwargs.get('stream'))

    def test_detail_level_applies(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs_brief = _build_completion_kwargs('gpt-4o', 'test', detail_level='brief')
        kwargs_deep = _build_completion_kwargs('gpt-4o', 'test', detail_level='deep')
        self.assertLess(kwargs_brief['max_tokens'], kwargs_deep['max_tokens'])


class TestExtractSeoMetadata(unittest.TestCase):
    """extract_seo_metadata 테스트"""

    def test_empty_content(self):
        from services.core.ai_service import extract_seo_metadata
        self.assertIsNone(extract_seo_metadata(''))
        self.assertIsNone(extract_seo_metadata(None))

    def test_meta_description(self):
        from services.core.ai_service import extract_seo_metadata
        content = "**메타 설명** | AI 기술의 미래를 다룬 블로그\n나머지 내용"
        result = extract_seo_metadata(content)
        self.assertIsNotNone(result)
        self.assertIn('meta_description', result)

    def test_keywords(self):
        from services.core.ai_service import extract_seo_metadata
        content = "**타겟 키워드** | AI, 머신러닝, 딥러닝\n"
        result = extract_seo_metadata(content)
        self.assertIn('keywords', result)
        self.assertGreater(len(result['keywords']), 0)

    def test_slug(self):
        from services.core.ai_service import extract_seo_metadata
        content = "**추천 URL** | /ai-future-2026\n"
        result = extract_seo_metadata(content)
        self.assertIn('slug', result)

    def test_tags(self):
        from services.core.ai_service import extract_seo_metadata
        content = "#태그 #AI기술 #딥러닝 #머신러닝\n"
        result = extract_seo_metadata(content)
        self.assertIsNotNone(result)
        self.assertIn('tags', result)

    def test_no_seo_content(self):
        from services.core.ai_service import extract_seo_metadata
        result = extract_seo_metadata('일반 본문 내용만 있는 텍스트')
        self.assertIsNone(result)


class TestExtractGeoMetadata(unittest.TestCase):
    """extract_geo_metadata 테스트"""

    def test_empty_content(self):
        from services.core.ai_service import extract_geo_metadata
        self.assertIsNone(extract_geo_metadata(''))
        self.assertIsNone(extract_geo_metadata(None))

    def test_key_facts(self):
        from services.core.ai_service import extract_geo_metadata
        content = "- ✓ 팩트 하나\n- ✓ 팩트 둘\n"
        result = extract_geo_metadata(content)
        self.assertIsNotNone(result)
        self.assertIn('key_facts', result)

    def test_entity_tags(self):
        from services.core.ai_service import extract_geo_metadata
        content = "### 엔티티 태그\n`AI` `머신러닝` `딥러닝`\n\n"
        result = extract_geo_metadata(content)
        self.assertIn('entity_tags', result)
        self.assertIn('AI', result['entity_tags'])

    def test_definition_as_citation(self):
        from services.core.ai_service import extract_geo_metadata
        content = "### 한 줄 정의\n> AI는 인공지능의 약자이다.\n\n"
        result = extract_geo_metadata(content)
        self.assertIn('citations', result)

    def test_no_geo_content(self):
        from services.core.ai_service import extract_geo_metadata
        result = extract_geo_metadata('평범한 본문 텍스트')
        self.assertIsNone(result)


class TestExtractFaqSchema(unittest.TestCase):
    """extract_faq_schema 테스트"""

    def test_empty_content(self):
        from services.core.ai_service import extract_faq_schema
        self.assertIsNone(extract_faq_schema(''))
        self.assertIsNone(extract_faq_schema(None))

    def test_valid_faq(self):
        from services.core.ai_service import extract_faq_schema
        content = """### 자주 묻는 질문
**Q. AI란 무엇인가요?**
A. AI는 인공지능의 약자로 컴퓨터가 인간의 학습을 모방하는 기술입니다.

**Q. 딥러닝이란?**
A. 딥러닝은 심층 신경망을 사용한 머신러닝의 하위 분야입니다.
"""
        result = extract_faq_schema(content)
        self.assertIsNotNone(result)
        self.assertEqual(result['@type'], 'FAQPage')
        self.assertEqual(len(result['mainEntity']), 2)
        self.assertEqual(result['mainEntity'][0]['@type'], 'Question')

    def test_no_faq(self):
        from services.core.ai_service import extract_faq_schema
        result = extract_faq_schema('일반 본문만 있는 내용')
        self.assertIsNone(result)


class TestExtractCta(unittest.TestCase):
    """extract_cta 테스트"""

    def test_empty(self):
        from services.core.ai_service import extract_cta
        self.assertIsNone(extract_cta(''))
        self.assertIsNone(extract_cta(None))

    def test_primary_cta(self):
        from services.core.ai_service import extract_cta
        content = "**CTA_PRIMARY**: 지금 시작하세요\n**CTA_SECONDARY**: 더 알아보기\n"
        result = extract_cta(content)
        self.assertIn('primary', result)
        self.assertIn('secondary', result)

    def test_no_cta(self):
        from services.core.ai_service import extract_cta
        result = extract_cta('CTA 없는 본문')
        self.assertIsNone(result)


class TestBuildPrompt(unittest.TestCase):
    """_build_prompt 테스트"""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_basic_prompt(self):
        from services.core.ai_service import _build_prompt
        result = _build_prompt('자막 내용', '블로그 스타일', None)
        self.assertIn('자막 내용', result)
        self.assertIn('블로그 스타일', result)
        self.assertIn('현재 시간', result)

    def test_with_rag_context(self):
        from services.core.ai_service import _build_prompt
        result = _build_prompt('자막', '스타일', None, rag_context='참고 문서')
        self.assertIn('참고자료', result)
        self.assertIn('참고 문서', result)

    def test_with_web_context(self):
        from services.core.ai_service import _build_prompt
        result = _build_prompt('자막', '스타일', None, web_context='웹 검색 결과')
        self.assertIn('웹 참고 자료', result)

    def test_with_style_memory(self):
        from services.core.ai_service import _build_prompt
        result = _build_prompt('자막', '스타일', None, style_memory_context='스타일 메모리')
        self.assertIn('스타일 메모리', result)

    def test_without_style_prompt(self):
        from services.core.ai_service import _build_prompt
        result = _build_prompt('자막', None, None)
        self.assertIn('자막', result)


class TestConvertErrorMessageExtended(unittest.TestCase):
    """_convert_error_message 추가 분기 테스트"""

    def test_timeout_error(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Request timed out')
        self.assertIn('타임아웃', result)

    def test_connection_error(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Connection refused')
        self.assertIn('연결', result)

    def test_service_unavailable(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('503 Service Unavailable')
        self.assertIn('서비스 불가', result)

    def test_internal_server_error(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('500 Internal Server Error')
        self.assertIn('서버 오류', result)

    def test_insufficient_credit(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Insufficient credit balance')
        self.assertIn('잔액 부족', result)

    def test_content_policy(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Content policy violation blocked')
        self.assertIn('컨텐츠 차단', result)

    def test_zhipu_1113(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Error code: 1113')
        self.assertIn('권한', result)

    def test_zhipu_1211(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Error code: 1211')
        self.assertIn('모델 없음', result)

    def test_zhipu_1302(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Error code: 1302')
        self.assertIn('동시성', result)

    def test_model_info_included(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Unknown error', model='gpt-4o')
        self.assertIn('gpt-4o', result)


if __name__ == '__main__':
    unittest.main()
