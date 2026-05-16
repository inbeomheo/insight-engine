"""search_index_service 단위 테스트"""
import unittest

from services.content.search_index_service import (
    build_index,
    search,
    _tokenize,
)


class TestBuildIndex(unittest.TestCase):

    def test_empty(self):
        result = build_index([])
        self.assertEqual(result['documents'], 0)
        self.assertEqual(result['terms'], 0)

    def test_single_document(self):
        contents = [{'id': '1', 'title': '인공지능', 'content': '머신러닝 딥러닝'}]
        result = build_index(contents)
        self.assertEqual(result['documents'], 1)
        self.assertGreater(result['terms'], 0)

    def test_multiple_documents(self):
        contents = [
            {'id': '1', 'title': 'AI', 'content': '인공지능 기술'},
            {'id': '2', 'title': 'ML', 'content': '머신러닝 알고리즘'},
        ]
        result = build_index(contents)
        self.assertEqual(result['documents'], 2)

    def test_word_in_index(self):
        contents = [{'id': 'doc1', 'title': '', 'content': '파이썬 프로그래밍'}]
        result = build_index(contents)
        self.assertIn('파이썬', result['index'])

    def test_frequency_counted(self):
        contents = [{'id': '1', 'title': '', 'content': '반복 반복 반복'}]
        result = build_index(contents)
        entries = result['index'].get('반복', [])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['frequency'], 3)

    def test_stopwords_excluded(self):
        contents = [{'id': '1', 'title': '', 'content': '그리고 하지만 따라서'}]
        result = build_index(contents)
        self.assertNotIn('그리고', result['index'])


class TestSearch(unittest.TestCase):

    def setUp(self):
        self.contents = [
            {'id': 'a', 'title': '인공지능 입문', 'content': '머신러닝과 딥러닝을 배웁니다'},
            {'id': 'b', 'title': '웹 개발', 'content': '파이썬 플라스크로 웹 서비스를 만듭니다'},
            {'id': 'c', 'title': '데이터 분석', 'content': '파이썬으로 데이터를 분석하고 시각화합니다'},
        ]
        self.index = build_index(self.contents)

    def test_basic_search(self):
        result = search(self.index, '인공지능')
        self.assertGreater(result['total'], 0)
        self.assertEqual(result['results'][0]['id'], 'a')

    def test_no_results(self):
        result = search(self.index, '양자역학')
        self.assertEqual(result['total'], 0)

    def test_empty_query(self):
        result = search(self.index, '')
        self.assertEqual(result['total'], 0)

    def test_empty_index(self):
        result = search({}, '테스트')
        self.assertEqual(result['total'], 0)

    def test_max_results(self):
        result = search(self.index, '파이썬', max_results=1)
        self.assertLessEqual(result['total'], 1)

    def test_score_normalized(self):
        result = search(self.index, '머신러닝')
        if result['results']:
            self.assertEqual(result['results'][0]['score'], 1.0)

    def test_matched_terms(self):
        result = search(self.index, '인공지능 머신러닝')
        if result['results']:
            self.assertGreater(len(result['results'][0]['matched_terms']), 0)

    def test_query_terms_returned(self):
        result = search(self.index, '파이썬 개발')
        self.assertIn('파이썬', result['query_terms'])

    def test_multi_term_boost(self):
        # 여러 쿼리 단어가 매칭되는 문서가 더 높은 점수
        result = search(self.index, '파이썬 데이터 분석')
        if len(result['results']) > 1:
            # 'c'(데이터 분석 + 파이썬)가 'b'(파이썬만)보다 높아야 함
            ids = [r['id'] for r in result['results']]
            self.assertEqual(ids[0], 'c')

    def test_results_sorted_by_score(self):
        result = search(self.index, '파이썬')
        scores = [r['score'] for r in result['results']]
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestTokenize(unittest.TestCase):

    def test_korean(self):
        tokens = _tokenize('한국어 텍스트입니다')
        self.assertIn('한국어', tokens)

    def test_english(self):
        tokens = _tokenize('hello world test')
        self.assertIn('hello', tokens)

    def test_stopwords_removed(self):
        tokens = _tokenize('그리고 중요한 내용입니다')
        self.assertNotIn('그리고', tokens)

    def test_empty(self):
        self.assertEqual(_tokenize(''), [])

    def test_lowered(self):
        tokens = _tokenize('Hello WORLD')
        self.assertIn('hello', tokens)


if __name__ == '__main__':
    unittest.main()
