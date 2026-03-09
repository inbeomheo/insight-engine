"""
비디오 라이브러리 챗봇 서비스 테스트
"""

import unittest

from services.video_library_chatbot_service import (
    VideoEntry,
    VideoLibrary,
    ChatResponse,
    _create_library,
    add_video,
    search_library,
    answer_query,
    suggest_related,
)


class TestAddVideo(unittest.TestCase):
    """비디오 추가 테스트"""

    def test_add_single_video(self):
        """단일 비디오 추가"""
        lib = _create_library()
        lib = add_video(lib, {
            "video_id": "v1",
            "title": "Python 기초",
            "description": "파이썬 입문 강좌",
            "tags": ["python", "programming"],
            "duration_sec": 600,
        })
        self.assertEqual(len(lib.videos), 1)
        self.assertEqual(lib.videos[0].video_id, "v1")
        self.assertEqual(lib.videos[0].title, "Python 기초")

    def test_add_multiple_videos(self):
        """여러 비디오 추가"""
        lib = _create_library()
        for i in range(5):
            lib = add_video(lib, {"video_id": f"v{i}", "title": f"강좌 {i}"})
        self.assertEqual(len(lib.videos), 5)

    def test_add_video_default_values(self):
        """기본값으로 비디오 추가"""
        lib = _create_library()
        lib = add_video(lib, {"title": "테스트"})
        self.assertEqual(lib.videos[0].duration_sec, 0)
        self.assertEqual(lib.videos[0].tags, [])
        self.assertNotEqual(lib.videos[0].video_id, "")


class TestSearchLibrary(unittest.TestCase):
    """라이브러리 검색 테스트"""

    def setUp(self):
        self.lib = _create_library()
        self.lib = add_video(self.lib, {
            "video_id": "v1", "title": "Python 기초 강좌",
            "description": "초보자를 위한 파이썬 프로그래밍",
            "tags": ["python", "beginner"],
        })
        self.lib = add_video(self.lib, {
            "video_id": "v2", "title": "JavaScript 웹 개발",
            "description": "프론트엔드 개발 입문",
            "tags": ["javascript", "web", "frontend"],
        })
        self.lib = add_video(self.lib, {
            "video_id": "v3", "title": "React 컴포넌트",
            "description": "React 기초와 컴포넌트 설계",
            "tags": ["react", "javascript", "frontend"],
        })

    def test_search_by_title(self):
        """제목 키워드 검색"""
        results = search_library(self.lib, "Python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].video_id, "v1")

    def test_search_by_tag(self):
        """태그 검색"""
        results = search_library(self.lib, "javascript")
        self.assertEqual(len(results), 2)

    def test_search_by_description(self):
        """설명 검색"""
        results = search_library(self.lib, "초보자")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].video_id, "v1")

    def test_search_empty_query(self):
        """빈 검색어"""
        results = search_library(self.lib, "")
        self.assertEqual(results, [])

    def test_search_no_results(self):
        """결과 없는 검색"""
        results = search_library(self.lib, "machine learning")
        self.assertEqual(results, [])

    def test_search_relevance_order(self):
        """관련도 순 정렬 (제목 매칭이 태그보다 높음)"""
        results = search_library(self.lib, "React")
        self.assertEqual(results[0].video_id, "v3")

    def test_search_case_insensitive(self):
        """대소문자 구분 없는 검색"""
        results = search_library(self.lib, "python")
        self.assertEqual(len(results), 1)

    def test_search_multi_term(self):
        """복합 검색어"""
        results = search_library(self.lib, "javascript web")
        # v2는 title+description에 두 단어 모두 포함
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0].video_id, "v2")


class TestAnswerQuery(unittest.TestCase):
    """질의 응답 테스트"""

    def setUp(self):
        self.lib = _create_library()
        self.lib = add_video(self.lib, {
            "video_id": "v1", "title": "Python 튜토리얼",
            "description": "파이썬 프로그래밍 기초 학습",
            "tags": ["python"],
        })
        self.lib = add_video(self.lib, {
            "video_id": "v2", "title": "Django 웹 프레임워크",
            "description": "Django로 웹 개발하기",
            "tags": ["python", "django", "web"],
        })

    def test_answer_with_results(self):
        """결과 있는 질의 응답"""
        resp = answer_query(self.lib, "Python")
        self.assertIsInstance(resp, ChatResponse)
        self.assertGreater(len(resp.relevant_videos), 0)
        self.assertGreater(resp.confidence, 0.0)
        self.assertIn("관련 비디오", resp.answer)

    def test_answer_no_results(self):
        """결과 없는 질의"""
        resp = answer_query(self.lib, "quantum computing")
        self.assertEqual(resp.relevant_videos, [])
        self.assertEqual(resp.confidence, 0.0)

    def test_answer_empty_query(self):
        """빈 질의"""
        resp = answer_query(self.lib, "")
        self.assertEqual(resp.relevant_videos, [])
        self.assertIn("입력", resp.answer)

    def test_confidence_bound(self):
        """신뢰도 범위 (0.0 ~ 1.0)"""
        resp = answer_query(self.lib, "Python")
        self.assertGreaterEqual(resp.confidence, 0.0)
        self.assertLessEqual(resp.confidence, 1.0)


class TestSuggestRelated(unittest.TestCase):
    """관련 비디오 추천 테스트"""

    def setUp(self):
        self.lib = _create_library()
        self.lib = add_video(self.lib, {
            "video_id": "v1", "title": "Python 기초",
            "tags": ["python", "programming", "beginner"],
        })
        self.lib = add_video(self.lib, {
            "video_id": "v2", "title": "Python 고급",
            "tags": ["python", "programming", "advanced"],
        })
        self.lib = add_video(self.lib, {
            "video_id": "v3", "title": "JavaScript 기초",
            "tags": ["javascript", "programming", "beginner"],
        })
        self.lib = add_video(self.lib, {
            "video_id": "v4", "title": "요리 레시피",
            "tags": ["cooking", "recipe"],
        })

    def test_suggest_related_by_tags(self):
        """태그 기반 추천"""
        results = suggest_related(self.lib, "v1")
        self.assertGreater(len(results), 0)
        # v2 (python, programming 공유)가 v3 (programming, beginner 공유)보다 유사
        ids = [v.video_id for v in results]
        self.assertIn("v2", ids)

    def test_suggest_excludes_self(self):
        """자기 자신 제외"""
        results = suggest_related(self.lib, "v1")
        ids = [v.video_id for v in results]
        self.assertNotIn("v1", ids)

    def test_suggest_top_k(self):
        """top_k 제한"""
        results = suggest_related(self.lib, "v1", top_k=1)
        self.assertLessEqual(len(results), 1)

    def test_suggest_unknown_video(self):
        """존재하지 않는 비디오"""
        results = suggest_related(self.lib, "unknown")
        self.assertEqual(results, [])

    def test_suggest_no_tags(self):
        """태그 없는 비디오"""
        lib = _create_library()
        lib = add_video(lib, {"video_id": "v1", "title": "테스트", "tags": []})
        results = suggest_related(lib, "v1")
        self.assertEqual(results, [])

    def test_unrelated_video_excluded(self):
        """관련 없는 비디오는 결과에 포함 안 됨"""
        results = suggest_related(self.lib, "v1")
        ids = [v.video_id for v in results]
        self.assertNotIn("v4", ids)


if __name__ == "__main__":
    unittest.main()
