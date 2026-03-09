"""AI 콘텐츠 인덱스 서비스 테스트"""

import unittest
from datetime import datetime, timedelta
from services.ai_content_index_service import (
    IndexEntry, ContentIndex,
    index_content, search_index, generate_sitemap, remove_stale,
)


class TestAIContentIndexService(unittest.TestCase):
    """AI 콘텐츠 인덱스 서비스 테스트"""

    def _make_index(self):
        return ContentIndex(index_id="idx1", entries=[])

    def test_index_content_basic(self):
        """기본 인덱싱"""
        idx = self._make_index()
        idx = index_content(idx, "https://example.com/1", "제목", "이것은 테스트 콘텐츠입니다. 키워드 추출 테스트.")
        self.assertEqual(len(idx.entries), 1)
        self.assertEqual(idx.entries[0].url, "https://example.com/1")

    def test_index_content_keywords(self):
        """키워드 자동 추출"""
        idx = self._make_index()
        idx = index_content(idx, "https://a.com", "제목", "파이썬 파이썬 프로그래밍 프로그래밍 프로그래밍 개발")
        entry = idx.entries[0]
        self.assertTrue(len(entry.keywords) > 0)
        # 빈도 높은 '프로그래밍'이 상위
        self.assertEqual(entry.keywords[0], "프로그래밍")

    def test_index_content_summary(self):
        """요약 자동 생성"""
        idx = self._make_index()
        content = "첫 번째 문장입니다. " * 20
        idx = index_content(idx, "https://a.com", "제목", content)
        self.assertTrue(len(idx.entries[0].summary) <= 210)  # 200 + margin

    def test_index_content_update_existing(self):
        """기존 URL 업데이트"""
        idx = self._make_index()
        idx = index_content(idx, "https://a.com", "제목1", "내용1")
        idx = index_content(idx, "https://a.com", "제목2", "내용2")
        self.assertEqual(len(idx.entries), 1)
        self.assertEqual(idx.entries[0].title, "제목2")

    def test_index_content_structured_data(self):
        """구조화 데이터 포함"""
        idx = self._make_index()
        idx = index_content(idx, "https://a.com", "제목", "내용")
        sd = idx.entries[0].structured_data
        self.assertEqual(sd["@type"], "Article")
        self.assertEqual(sd["name"], "제목")

    def test_search_index_keyword_match(self):
        """키워드 검색"""
        idx = self._make_index()
        idx = index_content(idx, "https://a.com", "Python 튜토리얼", "파이썬 프로그래밍 입문 가이드")
        results = search_index(idx, "python")
        self.assertEqual(len(results), 1)

    def test_search_index_no_match(self):
        """매칭 없음"""
        idx = self._make_index()
        idx = index_content(idx, "https://a.com", "제목", "내용")
        results = search_index(idx, "xyz없는키워드")
        self.assertEqual(len(results), 0)

    def test_search_index_ranking(self):
        """검색 결과 랭킹 — 키워드 매칭이 상위"""
        idx = self._make_index()
        idx = index_content(idx, "https://a.com", "파이썬 가이드", "파이썬 프로그래밍 입문")
        idx = index_content(idx, "https://b.com", "기타 글", "일반적인 내용의 글입니다")
        results = search_index(idx, "파이썬")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].url, "https://a.com")

    def test_generate_sitemap(self):
        """XML 사이트맵 생성"""
        idx = self._make_index()
        idx = index_content(idx, "https://a.com/1", "제목1", "내용1")
        idx = index_content(idx, "https://b.com/2", "제목2", "내용2")
        sitemap = generate_sitemap(idx)
        self.assertIn('<?xml version="1.0"', sitemap)
        self.assertIn("<loc>https://a.com/1</loc>", sitemap)
        self.assertIn("<loc>https://b.com/2</loc>", sitemap)

    def test_remove_stale(self):
        """오래된 항목 제거"""
        idx = self._make_index()
        old_date = (datetime.now() - timedelta(days=100)).isoformat()
        fresh_date = datetime.now().isoformat()

        idx.entries = [
            IndexEntry("e1", "https://old.com", "오래된", "", [], {}, old_date),
            IndexEntry("e2", "https://new.com", "최신", "", [], {}, fresh_date),
        ]

        idx = remove_stale(idx, 30, datetime.now().isoformat())
        self.assertEqual(len(idx.entries), 1)
        self.assertEqual(idx.entries[0].url, "https://new.com")

    def test_remove_stale_none_removed(self):
        """제거 대상 없음"""
        idx = self._make_index()
        idx = index_content(idx, "https://a.com", "제목", "내용")
        original_count = len(idx.entries)
        idx = remove_stale(idx, 365, datetime.now().isoformat())
        self.assertEqual(len(idx.entries), original_count)

    def test_generate_sitemap_empty(self):
        """빈 인덱스 사이트맵"""
        idx = self._make_index()
        sitemap = generate_sitemap(idx)
        self.assertIn("</urlset>", sitemap)


if __name__ == "__main__":
    unittest.main()
