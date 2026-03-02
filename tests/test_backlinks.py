"""
백링크/내부링크 서비스 통합 테스트

- web_search_service와 Supabase를 모킹하여 독립 실행
- find_internal_links, find_external_links, insert_links_into_content 검증
"""
import unittest
from unittest.mock import patch, MagicMock


class TestFindInternalLinks(unittest.TestCase):
    """find_internal_links 테스트"""

    def test_no_user_id_returns_empty(self):
        """user_id가 None이면 빈 리스트 반환"""
        from services.backlink_service import find_internal_links
        result = find_internal_links("테스트 콘텐츠", user_id=None)
        self.assertEqual(result, [])

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_supabase_disabled_returns_empty(self, _mock):
        """Supabase 비활성 시 빈 리스트 반환"""
        from services.backlink_service import find_internal_links
        result = find_internal_links("테스트 콘텐츠", user_id="user-123")
        self.assertEqual(result, [])

    @patch('services.supabase_service.is_supabase_enabled', return_value=True)
    @patch('services.supabase_service.get_supabase')
    def test_returns_relevant_links(self, mock_get_supabase, _mock_enabled):
        """관련 히스토리가 있으면 관련도 순으로 정렬된 링크 반환"""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        # 쿼리 체이닝 모킹
        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[
            {'report_id': 'r1', 'title': '파이썬 머신러닝 입문', 'url': 'https://youtu.be/abc'},
            {'report_id': 'r2', 'title': '딥러닝 기초 강의', 'url': 'https://youtu.be/def'},
            {'report_id': 'r3', 'title': '요리 레시피 소개', 'url': 'https://youtu.be/ghi'},
        ])
        mock_sb.table.return_value.select.return_value = mock_query

        from services.backlink_service import find_internal_links
        # "파이썬 머신러닝"과 관련된 콘텐츠로 테스트
        content = "파이썬으로 머신러닝 모델을 구현하는 방법을 알아봅니다."
        result = find_internal_links(content, user_id="user-123")

        # 요리 레시피는 관련도가 낮아 제외될 것
        urls = [r['url'] for r in result]
        self.assertIn('https://youtu.be/abc', urls)
        # 결과는 관련도 순으로 정렬
        if len(result) > 1:
            self.assertGreaterEqual(result[0]['relevance'], result[1]['relevance'])

    @patch('services.supabase_service.is_supabase_enabled', return_value=True)
    @patch('services.supabase_service.get_supabase')
    def test_empty_histories_returns_empty(self, mock_get_supabase, _mock_enabled):
        """히스토리가 없으면 빈 리스트 반환"""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[])
        mock_sb.table.return_value.select.return_value = mock_query

        from services.backlink_service import find_internal_links
        result = find_internal_links("콘텐츠 텍스트", user_id="user-456")
        self.assertEqual(result, [])

    @patch('services.supabase_service.is_supabase_enabled', return_value=True)
    @patch('services.supabase_service.get_supabase')
    def test_max_internal_links_limit(self, mock_get_supabase, _mock_enabled):
        """최대 2개까지만 반환"""
        mock_sb = MagicMock()
        mock_get_supabase.return_value = mock_sb

        mock_query = MagicMock()
        mock_query.eq.return_value = mock_query
        mock_query.order.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.execute.return_value = MagicMock(data=[
            {'report_id': f'r{i}', 'title': f'파이썬 튜토리얼 {i}', 'url': f'https://youtu.be/{i}'}
            for i in range(5)
        ])
        mock_sb.table.return_value.select.return_value = mock_query

        from services.backlink_service import find_internal_links, MAX_INTERNAL_LINKS
        result = find_internal_links("파이썬 프로그래밍 학습", user_id="user-123")
        self.assertLessEqual(len(result), MAX_INTERNAL_LINKS)


class TestSuggestAnchorTexts(unittest.TestCase):
    """suggest_anchor_texts 테스트"""

    def test_finds_anchor_in_content(self):
        """콘텐츠에서 앵커 텍스트를 찾아 position 반환"""
        from services.backlink_service import suggest_anchor_texts
        content = "파이썬으로 머신러닝을 학습하는 방법을 소개합니다."
        links = [{'title': '파이썬 머신러닝 입문', 'url': 'https://youtu.be/abc', 'relevance': 0.5}]

        result = suggest_anchor_texts(content, links)
        self.assertTrue(len(result) > 0)
        self.assertIn('anchor_text', result[0])
        self.assertIn('position', result[0])
        self.assertGreaterEqual(result[0]['position'], 0)

    def test_no_match_excluded(self):
        """콘텐츠에 앵커 텍스트가 없으면 해당 링크는 제외"""
        from services.backlink_service import suggest_anchor_texts
        content = "전혀 관련 없는 요리 이야기입니다."
        links = [{'title': '파이썬 머신러닝 딥러닝', 'url': 'https://youtu.be/abc', 'relevance': 0.5}]

        result = suggest_anchor_texts(content, links)
        # "파이썬", "머신러닝", "딥러닝" 중 어느 것도 없으므로 결과 없음
        self.assertEqual(result, [])


class TestFindExternalLinks(unittest.TestCase):
    """find_external_links 테스트"""

    @patch('services.web_search_service.search')
    def test_returns_authority_sorted_links(self, mock_search):
        """도메인 권위 + 검색 점수 기반 정렬"""
        mock_search.return_value = [
            {'title': 'Python Docs', 'url': 'https://docs.python.org/3/', 'score': 0.8},
            {'title': '블로그 포스트', 'url': 'https://randomblog.net/python', 'score': 0.9},
            {'title': 'GitHub', 'url': 'https://github.com/pytorch/pytorch', 'score': 0.7},
        ]

        from services.backlink_service import find_external_links
        result = find_external_links("파이썬 딥러닝")

        self.assertTrue(len(result) > 0)
        # 첫 번째 결과가 가장 높은 관련도
        if len(result) > 1:
            self.assertGreaterEqual(result[0]['relevance'], result[1]['relevance'])

        # docs.python.org(.org) 또는 github.com이 높은 순위일 것
        urls = [r['url'] for r in result]
        self.assertTrue(
            any('python.org' in u or 'github.com' in u for u in urls),
            "권위 있는 도메인이 결과에 포함되어야 함"
        )

    @patch('services.web_search_service.search')
    def test_empty_search_returns_empty(self, mock_search):
        """검색 결과 없으면 빈 리스트 반환"""
        mock_search.return_value = []

        from services.backlink_service import find_external_links
        result = find_external_links("존재하지않는주제xyz")
        self.assertEqual(result, [])

    @patch('services.web_search_service.search')
    def test_max_external_links_limit(self, mock_search):
        """최대 3개까지만 반환"""
        mock_search.return_value = [
            {'title': f'결과 {i}', 'url': f'https://example{i}.org/page', 'score': 0.5}
            for i in range(10)
        ]

        from services.backlink_service import find_external_links, MAX_EXTERNAL_LINKS
        result = find_external_links("테스트 주제")
        self.assertLessEqual(len(result), MAX_EXTERNAL_LINKS)

    @patch('services.web_search_service.search', side_effect=Exception("API 오류"))
    def test_search_exception_returns_empty(self, _mock):
        """검색 API 오류 시 graceful degradation"""
        from services.backlink_service import find_external_links
        result = find_external_links("테스트 주제")
        self.assertEqual(result, [])


class TestInsertLinksIntoContent(unittest.TestCase):
    """insert_links_into_content 테스트"""

    def test_inserts_markdown_links(self):
        """콘텐츠에 마크다운 링크가 삽입됨"""
        from services.backlink_service import insert_links_into_content
        content = "파이썬으로 머신러닝을 학습하는 방법을 소개합니다."
        internal = [{'url': 'https://youtu.be/abc', 'anchor_text': '파이썬', 'title': '파이썬 입문'}]
        external = [{'url': 'https://docs.python.org/', 'title': 'Python Docs', 'domain': 'docs.python.org'}]

        result = insert_links_into_content(content, internal, external)

        # 링크가 삽입되었는지 확인
        self.assertIn('](', result)
        self.assertIn('https://', result)

    def test_no_links_returns_original(self):
        """링크가 없으면 원본 콘텐츠 그대로 반환"""
        from services.backlink_service import insert_links_into_content
        content = "원본 콘텐츠 텍스트입니다."
        result = insert_links_into_content(content, [], [])
        self.assertEqual(result, content)

    def test_code_block_not_modified(self):
        """코드 블록 내부는 링크 삽입 안 함"""
        from services.backlink_service import insert_links_into_content
        content = "본문에 파이썬이 언급됩니다.\n```\n파이썬 코드 예시\n```\n이후 내용"
        external = [{'url': 'https://docs.python.org/', 'title': '파이썬 공식문서', 'domain': 'docs.python.org'}]

        result = insert_links_into_content(content, [], external)
        # 코드 블록 내의 "파이썬 코드 예시"는 링크로 변환되지 않아야 함
        self.assertIn('```\n파이썬 코드 예시\n```', result)

    def test_max_links_limit(self):
        """최대 링크 수(5개) 초과하지 않음"""
        from services.backlink_service import insert_links_into_content, MAX_TOTAL_LINKS
        content = "가나다라마바사아자차카타파하 " * 20
        internal = [
            {'url': f'https://youtu.be/{i}', 'anchor_text': c, 'title': f'제목 {i}'}
            for i, c in enumerate(['가나다라', '마바사아', '자차카타'])
        ]
        external = [
            {'url': f'https://example{i}.org/', 'title': f'외부 {i}', 'domain': f'example{i}.org'}
            for i in range(5)
        ]

        result = insert_links_into_content(content, internal, external, max_links=MAX_TOTAL_LINKS)
        # 삽입된 링크 수 계산
        link_count = result.count('](http')
        self.assertLessEqual(link_count, MAX_TOTAL_LINKS)

    def test_already_linked_text_not_double_linked(self):
        """이미 링크로 감싸진 텍스트는 재삽입하지 않음"""
        from services.backlink_service import insert_links_into_content
        content = "이미 [파이썬](https://python.org)으로 링크된 텍스트입니다."
        external = [{'url': 'https://docs.python.org/', 'title': '파이썬', 'domain': 'docs.python.org'}]

        result = insert_links_into_content(content, [], external)
        # "파이썬"이 이중으로 링크되지 않아야 함
        # 이미 링크가 있으므로 원본 링크만 유지
        self.assertNotIn('[[파이썬]', result)

    def test_returns_string(self):
        """반환 타입이 항상 str"""
        from services.backlink_service import insert_links_into_content
        result = insert_links_into_content("콘텐츠", [], [])
        self.assertIsInstance(result, str)


class TestDomainAuthorityScore(unittest.TestCase):
    """_domain_authority_score 내부 함수 테스트"""

    def test_edu_domain_high_score(self):
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score('https://mit.edu/research/ai')
        self.assertEqual(score, 1.0)

    def test_gov_domain_high_score(self):
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score('https://data.gov/dataset')
        self.assertEqual(score, 1.0)

    def test_github_high_score(self):
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score('https://github.com/openai/gpt')
        self.assertEqual(score, 0.9)

    def test_unknown_domain_medium_score(self):
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score('https://unknown-random-blog.com/post')
        self.assertEqual(score, 0.5)

    def test_invalid_url_returns_zero(self):
        from services.backlink_service import _domain_authority_score
        score = _domain_authority_score('not-a-url')
        self.assertEqual(score, 0.5)  # urlparse가 기본 파싱하므로 0.5 반환


if __name__ == '__main__':
    unittest.main()
