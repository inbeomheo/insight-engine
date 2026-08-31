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
        kwargs = _build_completion_kwargs('custom/local-model', 'test prompt')
        self.assertEqual(kwargs['model'], 'openai/gpt-5.6-sol')
        self.assertIn('messages', kwargs)
        self.assertNotIn('temperature', kwargs)
        self.assertIn('max_tokens', kwargs)

    def test_cliproxy_model(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('cliproxy/gpt-5.6-sol', 'test')
        self.assertNotIn('cliproxy/', kwargs['model'])
        self.assertEqual(kwargs['model'], 'openai/gpt-5.6-sol')
        self.assertEqual(kwargs['api_key'], 'test-cliproxy-key')
        self.assertEqual(kwargs['api_base'], 'http://cli-proxy-api:8317/v1')
        self.assertEqual(kwargs['reasoning_effort'], 'medium')
        self.assertTrue(kwargs.get('drop_params'))
        self.assertNotIn('temperature', kwargs)

    def test_raw_gpt_model_uses_cliproxy_base(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('gpt-5.4-mini', 'test')
        self.assertEqual(kwargs['model'], 'openai/gpt-5.4-mini')
        self.assertEqual(kwargs['api_base'], 'http://cli-proxy-api:8317/v1')
        self.assertEqual(kwargs['api_key'], 'test-cliproxy-key')

    def test_stream_flag(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs('cliproxy/gpt-5.4-mini', 'test', stream=True)
        self.assertTrue(kwargs.get('stream'))

    def test_detail_level_applies(self):
        from services.core.ai_service import _build_completion_kwargs
        kwargs_brief = _build_completion_kwargs('custom/local-model', 'test', detail_level='brief')
        kwargs_deep = _build_completion_kwargs('custom/local-model', 'test', detail_level='deep')
        self.assertLess(kwargs_brief['max_tokens'], kwargs_deep['max_tokens'])

    def test_glm_short_brief_generation_reserves_reasoning_budget(self):
        from services.core.ai_service import _build_completion_kwargs

        kwargs = _build_completion_kwargs(
            'zai/glm-5.3-flash',
            '짧은 요약',
            modifiers={'length': 'short'},
            detail_level='brief',
        )

        self.assertEqual(kwargs['max_tokens'], 4000)
        self.assertEqual(kwargs['reasoning_effort'], 'low')

    def test_glm_kwargs_request_provider_side_rate_limit_retries(self):
        from services.core.ai_service import _build_completion_kwargs

        kwargs = _build_completion_kwargs(
            'zai/glm-5.3-flash',
            '짧은 요약',
            modifiers={'length': 'short'},
        )

        self.assertGreaterEqual(kwargs.get('num_retries', 0), 2)
        cliproxy_kwargs = _build_completion_kwargs('cliproxy/gpt-5.6-sol', 'test')
        self.assertNotIn('num_retries', cliproxy_kwargs)


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
        self.assertEqual(result['key_facts'], ['팩트 하나', '팩트 둘'])

    def test_key_facts_ignores_dividers_and_hyphens(self):
        """구분선(---), 표 구분자, 단어 중간 하이픈은 key_facts에 수집되지 않는다."""
        from services.core.ai_service import extract_geo_metadata
        content = (
            "### 주요 팩트\n"
            "- ✓ RAG는 3단계 구조다\n"
            "- ✓ 정확도 15~25% 향상\n"
            "\n"
            "---\n"
            "\n"
            "### 구조화 데이터\n"
            "| 항목 | 내용 |\n"
            "|------|------|\n"
            "| **핵심 개념** | RAG |\n"
            "\n"
            "### CTA (Call-to-Action)\n"
            "**CTA_PRIMARY**: 문서 보기\n"
        )
        result = extract_geo_metadata(content)
        self.assertIsNotNone(result)
        self.assertEqual(result['key_facts'], ['RAG는 3단계 구조다', '정확도 15~25% 향상'])
        # 쓰레기 항목이 섞이지 않았는지 명시적으로 확인
        for fact in result['key_facts']:
            self.assertNotIn('--', fact)
            self.assertNotIn('to-Action', fact)

    def test_key_facts_without_checkmark_not_collected(self):
        """✓ 마커 없는 일반 불릿은 주요 팩트로 수집되지 않는다 (다른 섹션 불릿 오수집 방지)."""
        from services.core.ai_service import extract_geo_metadata
        content = (
            "### 주요 특징\n"
            "- 일반 불릿 항목\n"
            "- 또 다른 불릿\n"
        )
        result = extract_geo_metadata(content)
        # key_facts가 없거나(전체 None), 있어도 일반 불릿은 포함하지 않음
        if result is not None:
            self.assertNotIn('key_facts', result)

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

    def test_zai_rate_limit_error_is_actionable_and_hides_provider_internals(self):
        from services.core.ai_service import _convert_error_message

        result = _convert_error_message(
            'litellm.RateLimitError: ZaiException - Rate limit reached for requests',
            model='zai/glm-5.3-flash',
        )

        self.assertTrue(result.startswith('[요청 제한]'))
        self.assertIn('Z.AI', result)
        self.assertIn('OPEN AI 모델', result)
        self.assertNotIn('litellm', result.lower())

    def test_connection_error(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Connection refused')
        self.assertIn('연결', result)

    def test_cliproxy_connection_error_has_setup_hint(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Connection refused', model='cliproxy/gpt-5.6-sol')
        self.assertIn('CLIProxyAPI 연결 실패', result)
        self.assertIn('CLIPROXY_BASE_URL', result)

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

    def test_unknown_numeric_error_uses_generic_ai_error(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Error code: 1113')
        self.assertIn('AI 오류', result)
        self.assertIn('1113', result)

    def test_model_info_included(self):
        from services.core.ai_service import _convert_error_message
        result = _convert_error_message('Unknown error', model='gpt-4o')
        self.assertIn('gpt-4o', result)


if __name__ == '__main__':
    unittest.main()
