"""멀티소스 큐레이션 서비스 테스트"""

import unittest

from services.multisource_curation_service import (
    CurationSource,
    CuratedItem,
    CurationCollection,
    add_source,
    curate,
    rank_items,
    deduplicate,
)


class TestAddSource(unittest.TestCase):
    """add_source 함수 테스트"""

    def test_출처_추가(self):
        sources = []
        result = add_source(sources, "테크 블로그", "blog", 0.8)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "테크 블로그")
        self.assertEqual(result[0].source_type, "blog")

    def test_신뢰도_클리핑(self):
        sources = []
        result = add_source(sources, "출처", "news", 1.5)
        self.assertEqual(result[0].reliability, 1.0)

    def test_음수_신뢰도(self):
        sources = []
        result = add_source(sources, "출처", "news", -0.5)
        self.assertEqual(result[0].reliability, 0.0)

    def test_기존_리스트_보존(self):
        sources = [CurationSource(source_id="s1", name="기존")]
        result = add_source(sources, "신규", "paper", 0.9)
        self.assertEqual(len(result), 2)


class TestCurate(unittest.TestCase):
    """curate 함수 테스트"""

    def setUp(self):
        self.sources = [
            CurationSource(source_id="s1", name="블로그", source_type="blog", reliability=0.8),
            CurationSource(source_id="s2", name="뉴스", source_type="news", reliability=0.9),
        ]

    def test_관련_콘텐츠_큐레이션(self):
        candidates = [
            {"title": "머신러닝 입문", "summary": "머신러닝 기초를 다룹니다", "source_id": "s1"},
            {"title": "요리 레시피", "summary": "파스타 만들기", "source_id": "s2"},
        ]
        collection = curate("머신러닝", candidates, self.sources)
        self.assertGreater(len(collection.items), 0)
        # 관련 있는 것만 포함
        titles = [item.title for item in collection.items]
        self.assertIn("머신러닝 입문", titles)

    def test_출처_미매칭_제외(self):
        candidates = [
            {"title": "테스트", "summary": "테스트 내용", "source_id": "unknown_id"},
        ]
        collection = curate("테스트", candidates, self.sources)
        self.assertEqual(len(collection.items), 0)

    def test_빈_후보(self):
        collection = curate("topic", [], self.sources)
        self.assertEqual(len(collection.items), 0)

    def test_토픽_설정(self):
        collection = curate("AI 기술", [], self.sources)
        self.assertEqual(collection.topic, "AI 기술")


class TestRankItems(unittest.TestCase):
    """rank_items 함수 테스트"""

    def test_복합_점수_정렬(self):
        source_high = CurationSource(source_id="s1", reliability=0.9)
        source_low = CurationSource(source_id="s2", reliability=0.3)

        items = [
            CuratedItem(item_id="1", title="낮은", relevance=0.3, source=source_low),
            CuratedItem(item_id="2", title="높은", relevance=0.9, source=source_high),
        ]
        collection = CurationCollection(items=items)
        ranked = rank_items(collection)
        self.assertEqual(ranked[0].item_id, "2")  # 높은 점수 우선

    def test_빈_컬렉션(self):
        collection = CurationCollection(items=[])
        ranked = rank_items(collection)
        self.assertEqual(len(ranked), 0)


class TestDeduplicate(unittest.TestCase):
    """deduplicate 함수 테스트"""

    def test_동일_제목_제거(self):
        source = CurationSource(source_id="s1")
        items = [
            CuratedItem(item_id="1", title="머신러닝 입문 가이드", source=source),
            CuratedItem(item_id="2", title="머신러닝 입문 가이드", source=source),
        ]
        collection = CurationCollection(items=items)
        result = deduplicate(collection)
        self.assertEqual(len(result.items), 1)

    def test_유사_제목_제거(self):
        source = CurationSource(source_id="s1")
        items = [
            CuratedItem(item_id="1", title="머신러닝 입문 가이드 시작하기 기초", source=source),
            CuratedItem(item_id="2", title="머신러닝 입문 가이드 시작하기 기본", source=source),
        ]
        collection = CurationCollection(items=items)
        result = deduplicate(collection)
        # 5개 중 4개 동일 → 유사도 0.8 이상 → 중복 제거
        self.assertEqual(len(result.items), 1)

    def test_다른_제목_보존(self):
        source = CurationSource(source_id="s1")
        items = [
            CuratedItem(item_id="1", title="머신러닝 가이드", source=source),
            CuratedItem(item_id="2", title="딥러닝 튜토리얼", source=source),
        ]
        collection = CurationCollection(items=items)
        result = deduplicate(collection)
        self.assertEqual(len(result.items), 2)

    def test_빈_컬렉션(self):
        collection = CurationCollection(items=[])
        result = deduplicate(collection)
        self.assertEqual(len(result.items), 0)


if __name__ == "__main__":
    unittest.main()
