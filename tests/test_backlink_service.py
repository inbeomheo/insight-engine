"""backlink_service 단위 테스트 (내부 유틸 위주)"""
import unittest

from services.backlink_service import (
    _domain_authority_score,
    _find_code_block_ranges,
    _is_in_code_block,
    _is_already_linked,
    _extract_key_phrase,
    suggest_anchor_texts,
    recommend_internal_links,
    insert_links_into_content,
    MAX_TOTAL_LINKS,
    MAX_INTERNAL_LINKS,
    MAX_EXTERNAL_LINKS,
)


class TestDomainAuthorityScore(unittest.TestCase):

    def test_edu_domain(self):
        """.edu 도메인 → 1.0"""
        self.assertEqual(_domain_authority_score('https://mit.edu/paper'), 1.0)

    def test_gov_domain(self):
        """.gov 도메인 → 1.0"""
        self.assertEqual(_domain_authority_score('https://data.gov/datasets'), 1.0)

    def test_known_high_authority(self):
        """알려진 고권위 도메인 → 0.9"""
        self.assertEqual(_domain_authority_score('https://github.com/repo'), 0.9)

    def test_unknown_domain(self):
        """알 수 없는 도메인 → 0.5"""
        self.assertEqual(_domain_authority_score('https://random-blog.xyz/post'), 0.5)

    def test_invalid_url(self):
        """잘못된 URL → 0.0 또는 0.5"""
        score = _domain_authority_score('')
        self.assertIn(score, [0.0, 0.5])


class TestFindCodeBlockRanges(unittest.TestCase):

    def test_no_code_blocks(self):
        """코드 블록 없음 → 빈 리스트"""
        self.assertEqual(_find_code_block_ranges('일반 텍스트입니다.'), [])

    def test_single_code_block(self):
        """단일 코드 블록"""
        content = '앞\n```python\nprint("hello")\n```\n뒤'
        ranges = _find_code_block_ranges(content)
        self.assertEqual(len(ranges), 1)

    def test_multiple_code_blocks(self):
        """복수 코드 블록"""
        content = '```\nA\n```\n중간\n```\nB\n```'
        ranges = _find_code_block_ranges(content)
        self.assertEqual(len(ranges), 2)


class TestIsInCodeBlock(unittest.TestCase):

    def test_inside(self):
        """코드 블록 내부 → True"""
        self.assertTrue(_is_in_code_block(15, [(10, 30)]))

    def test_outside(self):
        """코드 블록 외부 → False"""
        self.assertFalse(_is_in_code_block(5, [(10, 30)]))

    def test_empty_ranges(self):
        """빈 범위 → False"""
        self.assertFalse(_is_in_code_block(10, []))


class TestIsAlreadyLinked(unittest.TestCase):

    def test_linked(self):
        """이미 링크된 텍스트 → True"""
        content = '여기 [링크](https://example.com) 있다'
        start = content.index('링크')
        end = start + len('링크')
        self.assertTrue(_is_already_linked(content, start, end))

    def test_not_linked(self):
        """링크되지 않은 텍스트 → False"""
        content = '여기 링크 텍스트가 있다'
        start = content.index('링크')
        end = start + len('링크')
        self.assertFalse(_is_already_linked(content, start, end))


class TestExtractKeyPhrase(unittest.TestCase):

    def test_basic(self):
        """제목에서 핵심 키워드 추출"""
        result = _extract_key_phrase('파이썬 머신러닝 튜토리얼')
        self.assertTrue(len(result) >= 2)

    def test_empty(self):
        """빈 제목 → 빈 문자열"""
        self.assertEqual(_extract_key_phrase(''), '')

    def test_special_chars_removed(self):
        """특수문자 제거 후 추출"""
        result = _extract_key_phrase('(고급) React: 실전 가이드!')
        self.assertNotIn('(', result)
        self.assertNotIn('!', result)


class TestSuggestAnchorTexts(unittest.TestCase):

    def test_found_anchor(self):
        """콘텐츠 내 앵커 텍스트 발견"""
        content = '파이썬은 좋은 프로그래밍 언어입니다.'
        links = [{'title': '파이썬 프로그래밍', 'url': 'https://example.com', 'relevance': 0.5}]
        result = suggest_anchor_texts(content, links)
        self.assertEqual(len(result), 1)
        self.assertIn('anchor_text', result[0])
        self.assertIn('position', result[0])

    def test_no_anchor_match(self):
        """콘텐츠에 단어 없음 → 결과 없음"""
        content = '오늘 날씨가 좋습니다.'
        links = [{'title': 'JavaScript Tutorial', 'url': 'https://example.com', 'relevance': 0.5}]
        result = suggest_anchor_texts(content, links)
        self.assertEqual(len(result), 0)


class TestRecommendInternalLinks(unittest.TestCase):

    def test_basic_recommendation(self):
        """관련 콘텐츠 추천"""
        content = '파이썬으로 머신러닝 모델을 학습합니다'
        existing = [
            {'id': '1', 'title': '파이썬 머신러닝 입문', 'url': 'https://a.com'},
            {'id': '2', 'title': '자바 웹 개발', 'url': 'https://b.com'},
        ]
        result = recommend_internal_links(content, existing)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]['url'], 'https://a.com')

    def test_empty_content(self):
        """빈 콘텐츠 → 빈 리스트"""
        self.assertEqual(recommend_internal_links('', [{'id': '1', 'title': 'T', 'url': 'u'}]), [])

    def test_empty_existing(self):
        """빈 기존 목록 → 빈 리스트"""
        self.assertEqual(recommend_internal_links('내용입니다', []), [])

    def test_max_internal_links(self):
        """최대 MAX_INTERNAL_LINKS개 반환"""
        content = '파이썬 머신러닝 딥러닝 데이터 분석'
        existing = [
            {'id': str(i), 'title': f'파이썬 머신러닝 주제 {i}', 'url': f'https://{i}.com'}
            for i in range(10)
        ]
        result = recommend_internal_links(content, existing)
        self.assertLessEqual(len(result), MAX_INTERNAL_LINKS)


class TestInsertLinksIntoContent(unittest.TestCase):

    def test_no_links(self):
        """링크 없으면 원본 반환"""
        content = '테스트 콘텐츠입니다.'
        self.assertEqual(insert_links_into_content(content, [], []), content)

    def test_insert_internal_link(self):
        """내부 링크 삽입"""
        content = '파이썬은 좋은 언어입니다.'
        internal = [{'url': 'https://a.com', 'anchor_text': '파이썬', 'title': '파이썬'}]
        result = insert_links_into_content(content, internal, [])
        self.assertIn('[파이썬](https://a.com)', result)

    def test_skip_code_block(self):
        """코드 블록 내부 키워드만 있으면 링크 삽입 안 됨"""
        content = '설명입니다.\n```\n딥러닝 코드\n```\n좋습니다.'
        internal = [{'url': 'https://a.com', 'anchor_text': '딥러닝', 'title': '딥러닝 기초'}]
        result = insert_links_into_content(content, internal, [])
        # 코드 블록 안의 '딥러닝'은 링크되지 않음
        self.assertNotIn('[딥러닝](https://a.com)', result)


if __name__ == '__main__':
    unittest.main()
