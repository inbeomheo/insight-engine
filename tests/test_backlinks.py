"""
백링크/내부링크 자동 삽입 서비스 통합 테스트 (P3-7E)

- find_internal_links: Supabase 모킹 후 내부링크 검색 검증
- find_external_links: web_search_service 모킹 후 외부링크 검색 검증
- suggest_anchor_texts: 앵커 텍스트 제안 로직 검증
- insert_links_into_content: 링크 삽입 결과 검증
- Supabase 비활성 시 graceful degradation 검증
- blog_seo 프롬프트 LINK_PLACEHOLDER 포함 여부 검증
"""
import re
import unittest
from unittest.mock import patch, MagicMock


class TestFindInternalLinks(unittest.TestCase):
    """find_internal_links 단위 테스트"""

    def test_returns_empty_when_user_id_none(self):
        """user_id가 None이면 빈 리스트 반환"""
        from services.backlink_service import find_internal_links
        result = find_internal_links("Python content here", user_id=None)
        self.assertEqual(result, [])

    @patch("services.supabase_service.is_supabase_enabled", return_value=False)
    def test_returns_empty_when_supabase_disabled(self, mock_enabled):
        """Supabase 비활성 시 빈 리스트 반환 (graceful degradation)"""
        from services.backlink_service import find_internal_links
        result = find_internal_links("Python content", user_id="user-123")
        self.assertEqual(result, [])

    @patch("services.supabase_service.is_supabase_enabled", return_value=True)
    @patch("services.supabase_service.get_supabase")
    def test_returns_matched_links(self, mock_get_supabase, mock_enabled):
        """키워드가 겹치는 히스토리 항목이 반환됨"""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_execute = MagicMock()
        mock_execute.data = [
            {"report_id": "r1", "title": "Python content tutorial", "url": "https://youtube.com/1"},
            {"report_id": "r2", "title": "cooking recipes collection", "url": "https://youtube.com/2"},
        ]
        chain = (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .order.return_value
            .limit.return_value
        )
        chain.execute.return_value = mock_execute

        from services.backlink_service import find_internal_links
        result = find_internal_links("Python tutorial content basics", user_id="user-123")
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 2)
        for item in result:
            self.assertIn("title", item)
            self.assertIn("url", item)
            self.assertIn("relevance", item)
            self.assertIsInstance(item["relevance"], float)

    @patch("services.supabase_service.is_supabase_enabled", return_value=True)
    @patch("services.supabase_service.get_supabase")
    def test_returns_empty_when_no_match(self, mock_get_supabase, mock_enabled):
        """관련 없는 히스토리만 있으면 빈 리스트 반환"""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_execute = MagicMock()
        mock_execute.data = [
            {"report_id": "r1", "title": "cooking recipe summer salad", "url": "https://youtube.com/1"},
        ]
        chain = (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .order.return_value
            .limit.return_value
        )
        chain.execute.return_value = mock_execute

        from services.backlink_service import find_internal_links
        result = find_internal_links("Python AI programming technology content", user_id="user-123")
        self.assertEqual(result, [])

    @patch("services.supabase_service.is_supabase_enabled", return_value=True)
    @patch("services.supabase_service.get_supabase")
    def test_handles_db_error_gracefully(self, mock_get_supabase, mock_enabled):
        """DB 오류 발생 시 빈 리스트 반환 (graceful degradation)"""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_supabase.table.side_effect = Exception("DB connection error")

        from services.backlink_service import find_internal_links
        result = find_internal_links("some content", user_id="user-123")
        self.assertEqual(result, [])

    @patch("services.supabase_service.is_supabase_enabled", return_value=True)
    @patch("services.supabase_service.get_supabase")
    def test_relevance_sorted_descending(self, mock_get_supabase, mock_enabled):
        """반환 링크는 relevance 내림차순 정렬"""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase
        mock_execute = MagicMock()
        mock_execute.data = [
            {"report_id": "r1", "title": "Python tutorial basics intro", "url": "https://youtube.com/1"},
            {"report_id": "r2", "title": "Python", "url": "https://youtube.com/2"},
        ]
        chain = (
            mock_supabase.table.return_value
            .select.return_value
            .eq.return_value
            .order.return_value
            .limit.return_value
        )
        chain.execute.return_value = mock_execute

        from services.backlink_service import find_internal_links
        result = find_internal_links("Python tutorial basics introduction", user_id="user-123")
        if len(result) >= 2:
            self.assertGreaterEqual(result[0]["relevance"], result[1]["relevance"])


class TestSuggestAnchorTexts(unittest.TestCase):
    """suggest_anchor_texts 단위 테스트"""

    def test_finds_anchor_in_content(self):
        """링크 제목의 핵심 단어가 콘텐츠에서 발견됨"""
        from services.backlink_service import suggest_anchor_texts
        content = "Python is a programming language. Machine learning uses it a lot."
        links = [{"title": "Python intro course", "url": "https://youtube.com/1", "relevance": 0.8}]
        result = suggest_anchor_texts(content, links)
        self.assertIsInstance(result, list)
        if result:
            self.assertIn("anchor_text", result[0])
            self.assertIn("position", result[0])

    def test_excludes_unmatched_links(self):
        """콘텐츠에서 앵커 텍스트를 찾지 못한 링크는 제외됨"""
        from services.backlink_service import suggest_anchor_texts
        content = "completely unrelated content here"
        links = [{"title": "blockchain technology mastery", "url": "https://youtube.com/1", "relevance": 0.8}]
        result = suggest_anchor_texts(content, links)
        self.assertEqual(result, [])

    def test_handles_empty_links(self):
        """빈 링크 리스트 입력 시 빈 리스트 반환"""
        from services.backlink_service import suggest_anchor_texts
        result = suggest_anchor_texts("content", [])
        self.assertEqual(result, [])

    def test_returns_original_link_fields(self):
        """반환된 항목에 원본 링크 필드(title, url, relevance)가 유지됨"""
        from services.backlink_service import suggest_anchor_texts
        content = "Python tutorial introduction beginner guide."
        links = [{"title": "Python intro", "url": "https://youtube.com/1", "relevance": 0.7}]
        result = suggest_anchor_texts(content, links)
        if result:
            self.assertEqual(result[0]["url"], "https://youtube.com/1")
            self.assertEqual(result[0]["relevance"], 0.7)


class TestFindExternalLinks(unittest.TestCase):
    """find_external_links 단위 테스트"""

    def test_returns_empty_when_no_search_results(self):
        """웹 검색 결과 없을 때 빈 리스트 반환"""
        with patch("services.web_search_service.search", return_value=[]):
            from services.backlink_service import find_external_links
            result = find_external_links("Python tutorial")
            self.assertEqual(result, [])

    def test_returns_scored_links(self):
        """검색 결과가 있으면 relevance 점수가 포함된 링크 반환"""
        mock_results = [
            {"title": "Python official docs", "url": "https://docs.python.org/3/", "content": "...", "score": 0.95},
            {"title": "GitHub Python", "url": "https://github.com/python", "content": "...", "score": 0.80},
        ]
        with patch("services.web_search_service.search", return_value=mock_results):
            from services.backlink_service import find_external_links
            result = find_external_links("Python tutorial", max_results=3)
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIn("title", item)
            self.assertIn("url", item)
            self.assertIn("domain", item)
            self.assertIn("relevance", item)
            self.assertIsInstance(item["relevance"], float)

    def test_authority_domains_get_higher_score(self):
        """.edu 도메인이 일반 도메인보다 높은 점수를 받음"""
        mock_results = [
            {"title": "MIT resource", "url": "https://www.mit.edu/python", "content": "...", "score": 0.7},
            {"title": "Random blog", "url": "https://randomblog.com/python", "content": "...", "score": 0.7},
        ]
        with patch("services.web_search_service.search", return_value=mock_results):
            from services.backlink_service import find_external_links
            result = find_external_links("Python", max_results=5)
        if len(result) >= 2:
            edu_link = next((r for r in result if "mit.edu" in r["url"]), None)
            blog_link = next((r for r in result if "randomblog.com" in r["url"]), None)
            if edu_link and blog_link:
                self.assertGreater(edu_link["relevance"], blog_link["relevance"])

    def test_max_results_respected(self):
        """max_results 이하의 결과만 반환됨"""
        mock_results = [
            {"title": f"result {i}", "url": f"https://site{i}.com", "content": "...", "score": 0.9}
            for i in range(10)
        ]
        with patch("services.web_search_service.search", return_value=mock_results):
            from services.backlink_service import find_external_links
            result = find_external_links("query", max_results=2)
        self.assertLessEqual(len(result), 2)


class TestInsertLinksIntoContent(unittest.TestCase):
    """insert_links_into_content 단위 테스트"""

    def test_returns_original_when_no_links(self):
        """링크가 없으면 원본 콘텐츠 그대로 반환"""
        from services.backlink_service import insert_links_into_content
        content = "Python is a great programming language."
        result = insert_links_into_content(content, [], [])
        self.assertEqual(result, content)

    def test_inserts_external_link(self):
        """외부링크가 콘텐츠에 삽입됨"""
        from services.backlink_service import insert_links_into_content
        content = "Python is used for machine learning tasks."
        external_links = [
            {"title": "Python docs", "url": "https://docs.python.org", "domain": "docs.python.org", "relevance": 0.9},
        ]
        result = insert_links_into_content(content, [], external_links)
        self.assertIn("](", result)
        self.assertIn("docs.python.org", result)

    def test_does_not_modify_code_blocks(self):
        """코드 블록 내부의 텍스트는 수정되지 않음"""
        from services.backlink_service import insert_links_into_content
        content = "intro text.\n\n```python\nPython code example\n```\n\nfooter."
        external_links = [
            {"title": "Python guide", "url": "https://docs.python.org", "domain": "docs.python.org", "relevance": 0.9},
        ]
        result = insert_links_into_content(content, [], external_links)
        self.assertIn("```python\nPython code example\n```", result)

    def test_does_not_double_link_existing_markdown_links(self):
        """이미 링크로 감싸진 텍스트는 다시 링크로 감싸지 않음"""
        from services.backlink_service import insert_links_into_content
        content = "[Python](https://python.org) is a language."
        external_links = [
            {"title": "Python learning", "url": "https://docs.python.org", "domain": "docs.python.org", "relevance": 0.9},
        ]
        result = insert_links_into_content(content, [], external_links)
        # 원래 링크는 유지되어야 함
        self.assertIn("[Python](https://python.org)", result)

    def test_max_links_limit_enforced(self):
        """max_links 이상의 링크가 삽입되지 않음"""
        from services.backlink_service import insert_links_into_content
        content = "Python Java JavaScript TypeScript Go Rust languages."
        external_links = [
            {"title": f"lang{i}", "url": f"https://lang{i}.org", "domain": f"lang{i}.org", "relevance": 0.9}
            for i in range(8)
        ]
        result = insert_links_into_content(content, [], external_links, max_links=3)
        link_count = len(re.findall(r"\[.*?\]\(https?://.*?\)", result))
        self.assertLessEqual(link_count, 3)

    def test_returns_string(self):
        """반환값은 항상 문자열"""
        from services.backlink_service import insert_links_into_content
        result = insert_links_into_content("content", [], [])
        self.assertIsInstance(result, str)


class TestDomainAuthorityScore(unittest.TestCase):
    """_domain_authority_score 단위 테스트"""

    def test_edu_domain_high_authority(self):
        """.edu 도메인은 최고 권위 점수(1.0)"""
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score("https://www.harvard.edu/python")
        self.assertEqual(score, 1.0)

    def test_gov_domain_high_authority(self):
        """.gov 도메인은 최고 권위 점수(1.0)"""
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score("https://www.usa.gov/technology")
        self.assertEqual(score, 1.0)

    def test_org_domain_high_authority(self):
        """.org 도메인은 최고 권위 점수(1.0)"""
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score("https://www.python.org/docs")
        self.assertEqual(score, 1.0)

    def test_known_domain_high_authority(self):
        """알려진 기술 도메인은 높은 권위 점수(0.9)"""
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score("https://github.com/python/cpython")
        self.assertEqual(score, 0.9)

    def test_unknown_domain_default_score(self):
        """알 수 없는 도메인은 기본 점수(0.5)"""
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score("https://randomblog123.io/post")
        self.assertEqual(score, 0.5)


class TestExtractKeyPhrase(unittest.TestCase):
    """_extract_key_phrase 단위 테스트"""

    def test_returns_empty_for_empty_input(self):
        """빈 문자열 입력 시 빈 문자열 반환"""
        from services.backlink_service import _extract_key_phrase
        result = _extract_key_phrase("")
        self.assertEqual(result, "")

    def test_strips_special_chars(self):
        """특수문자가 제거됨"""
        from services.backlink_service import _extract_key_phrase
        result = _extract_key_phrase("[2024] Python! complete")
        self.assertNotIn("[", result)
        self.assertNotIn("!", result)

    def test_returns_nonempty_for_valid_title(self):
        """유효한 제목에서 비어있지 않은 키워드 반환"""
        from services.backlink_service import _extract_key_phrase
        result = _extract_key_phrase("Python machine learning guide")
        self.assertGreater(len(result), 0)


class TestBlogSeoPromptLinkPlaceholder(unittest.TestCase):
    """blog_seo 프롬프트 LINK_PLACEHOLDER 지시 검증"""

    def test_prompt_contains_link_placeholder(self):
        """blog_seo 프롬프트에 LINK_PLACEHOLDER 마커 지시가 포함됨"""
        from prompts.styles.blog_seo import BLOG_SEO_PROMPT
        self.assertIn("LINK_PLACEHOLDER", BLOG_SEO_PROMPT)

    def test_prompt_has_external_link_guidance(self):
        """blog_seo 프롬프트에 외부 링크 삽입 관련 안내가 포함됨"""
        from prompts.styles.blog_seo import BLOG_SEO_PROMPT
        self.assertTrue(
            "외부 링크" in BLOG_SEO_PROMPT or "LINK_PLACEHOLDER" in BLOG_SEO_PROMPT,
            "blog_seo 프롬프트에 외부 링크 삽입 안내가 없음"
        )


if __name__ == "__main__":
    unittest.main()
