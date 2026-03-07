"""search_service 단위 테스트"""
import unittest

from services import search_service


class TestSearchService(unittest.TestCase):
    """검색 서비스 테스트"""

    def setUp(self):
        search_service._index.clear()

    def test_index_and_search(self):
        """인덱스 후 검색"""
        search_service.index_content('c1', 'Python 튜토리얼', '파이썬 기초 문법 설명')
        result = search_service.search('Python')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['results'][0]['id'], 'c1')

    def test_empty_query(self):
        """빈 검색어 시 빈 결과"""
        result = search_service.search('   ')
        self.assertEqual(result['total'], 0)

    def test_and_matching(self):
        """여러 검색어 AND 매칭"""
        search_service.index_content('c1', '제목', 'Python 기초')
        search_service.index_content('c2', '제목', 'Python 고급 JavaScript')
        result = search_service.search('Python JavaScript')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['results'][0]['id'], 'c2')

    def test_style_filter(self):
        """스타일 필터링"""
        search_service.index_content('c1', '블로그', '내용', style='blog_seo')
        search_service.index_content('c2', '블로그', '내용', style='tutorial')
        result = search_service.search('블로그', style_filter='tutorial')
        self.assertEqual(result['total'], 1)

    def test_title_weight(self):
        """제목 매칭이 본문보다 높은 점수"""
        search_service.index_content('c1', 'React', '프레임워크 설명')
        search_service.index_content('c2', '프레임워크', 'React 사용법')
        result = search_service.search('React')
        self.assertEqual(result['results'][0]['id'], 'c1')

    def test_pagination(self):
        """offset/limit 페이지네이션"""
        for i in range(10):
            search_service.index_content(f'c{i}', f'테스트 {i}', '공통 내용')
        result = search_service.search('테스트', limit=3, offset=2)
        self.assertEqual(len(result['results']), 3)
        self.assertEqual(result['total'], 10)

    def test_remove_from_index(self):
        """인덱스에서 제거"""
        search_service.index_content('c1', '제목', '내용')
        search_service.remove_from_index('c1')
        result = search_service.search('제목')
        self.assertEqual(result['total'], 0)

    def test_snippet_extraction(self):
        """검색 결과에 snippet 포함"""
        search_service.index_content('c1', '제목', '앞부분 ' * 20 + 'KEYWORD' + ' 뒷부분' * 20)
        result = search_service.search('KEYWORD')
        self.assertIn('snippet', result['results'][0])

    def test_case_insensitive(self):
        """대소문자 구분 없이 검색"""
        search_service.index_content('c1', 'JavaScript Guide', 'content')
        result = search_service.search('javascript')
        self.assertEqual(result['total'], 1)


if __name__ == '__main__':
    unittest.main()
