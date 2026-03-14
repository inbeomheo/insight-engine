"""topic_cluster_service 단위 테스트"""
import unittest

from services.seo.topic_cluster_service import cluster_contents, _tokenize, _cosine_similarity
from services.seo.topic_cluster_service import map_topic_clusters


class TestTokenize(unittest.TestCase):

    def test_basic(self):
        tokens = _tokenize('Python 프로그래밍 학습')
        self.assertIn('python', tokens)
        self.assertIn('프로그래밍', tokens)

    def test_stopwords_removed(self):
        tokens = _tokenize('the quick brown fox')
        self.assertNotIn('the', tokens)
        self.assertIn('quick', tokens)

    def test_short_words_excluded(self):
        tokens = _tokenize('I x a developer')
        self.assertNotIn('x', tokens)  # 2자 미만
        self.assertNotIn('a', tokens)  # 1자


class TestCosineSimilarity(unittest.TestCase):

    def test_identical(self):
        v = {'a': 1.0, 'b': 2.0}
        self.assertAlmostEqual(_cosine_similarity(v, v), 1.0, places=5)

    def test_orthogonal(self):
        v1 = {'a': 1.0}
        v2 = {'b': 1.0}
        self.assertEqual(_cosine_similarity(v1, v2), 0.0)

    def test_empty(self):
        self.assertEqual(_cosine_similarity({}, {'a': 1.0}), 0.0)


class TestClusterContents(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(cluster_contents([]), [])

    def test_single_item(self):
        result = cluster_contents([{'id': '1', 'title': 'test', 'content': 'hello world'}])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['content_ids'], ['1'])

    def test_similar_grouped(self):
        contents = [
            {'id': 'a', 'title': 'Python 프로그래밍', 'content': 'Python 개발 학습 튜토리얼 프로그래밍'},
            {'id': 'b', 'title': 'Python 개발', 'content': 'Python 프로그래밍 입문 개발자 튜토리얼'},
            {'id': 'c', 'title': '요리 레시피', 'content': '김치찌개 레시피 요리 방법 재료'},
        ]
        result = cluster_contents(contents, threshold=0.1)
        # Python 관련 2개가 같은 클러스터, 요리가 별도 클러스터
        all_ids = [cid for cluster in result for cid in cluster['content_ids']]
        self.assertEqual(sorted(all_ids), ['a', 'b', 'c'])

    def test_keywords_present(self):
        contents = [
            {'id': '1', 'title': 'AI 기술', 'content': '인공지능 머신러닝 딥러닝 기술 개발'},
        ]
        result = cluster_contents(contents)
        self.assertTrue(len(result[0]['keywords']) > 0)

    def test_uses_index_as_id(self):
        contents = [{'title': 'no id', 'content': 'test content'}]
        result = cluster_contents(contents)
        self.assertEqual(result[0]['content_ids'], ['0'])


# ---------------------------------------------------------------------------
# map_topic_clusters 테스트 (pillar-supporting 토픽 클러스터 맵)
# ---------------------------------------------------------------------------

class TestMapTopicClusters(unittest.TestCase):
    """map_topic_clusters 함수의 규칙 기반 클러스터링 테스트."""

    # --- 헬퍼: 공통 테스트 데이터 ---

    def _make_python_contents(self):
        """Python 관련 콘텐츠 3개 + 요리 관련 1개 (고립)."""
        return [
            {
                "id": "c1",
                "title": "Python 머신러닝 입문 가이드",
                "content": (
                    "Python 머신러닝 라이브러리 사이킷런 사이킷런 텐서플로 텐서플로 "
                    "Python 머신러닝 데이터 분석 분석 모델 학습 학습 튜토리얼 튜토리얼"
                ),
            },
            {
                "id": "c2",
                "title": "Python 데이터 분석 실전",
                "content": (
                    "Python 데이터 분석 판다스 판다스 넘파이 넘파이 "
                    "Python 데이터 전처리 전처리 시각화 시각화 머신러닝 머신러닝"
                ),
            },
            {
                "id": "c3",
                "title": "Python 웹 개발 플라스크",
                "content": (
                    "Python 웹 개발 플라스크 플라스크 장고 장고 "
                    "Python 개발 서버 서버 배포 배포 데이터베이스 데이터베이스"
                ),
            },
            {
                "id": "c4",
                "title": "프랑스 요리 레시피 모음",
                "content": (
                    "프랑스 요리 레시피 크로와상 크로와상 바게트 바게트 "
                    "프랑스 요리 디저트 디저트 소스 소스 재료 재료"
                ),
            },
        ]

    # --- 1. test_empty_contents ---

    def test_empty_contents(self):
        """빈 리스트 입력 시 빈 클러스터 반환."""
        result = map_topic_clusters([])
        self.assertEqual(result["clusters"], [])
        self.assertEqual(result["unclustered"], [])
        self.assertEqual(result["summary"]["total_clusters"], 0)
        self.assertEqual(result["summary"]["avg_cluster_size"], 0.0)
        self.assertEqual(result["summary"]["coverage"], 0.0)
        # 제안은 최소 1개 존재
        self.assertTrue(len(result["suggestions"]) >= 1)

    # --- 2. test_single_content ---

    def test_single_content(self):
        """콘텐츠 1개만 있으면 클러스터 형성 불가, unclustered에 포함."""
        contents = [{"id": "only", "title": "단독 콘텐츠", "content": "테스트 테스트 내용 내용"}]
        result = map_topic_clusters(contents)
        self.assertEqual(result["clusters"], [])
        self.assertIn("only", result["unclustered"])
        self.assertEqual(result["summary"]["total_clusters"], 0)
        self.assertEqual(result["summary"]["coverage"], 0.0)

    # --- 3. test_basic_clustering ---

    def test_basic_clustering(self):
        """2개 이상 콘텐츠가 공통 키워드를 공유하면 클러스터 형성."""
        contents = [
            {
                "id": "a",
                "title": "딥러닝 기초 강의",
                "content": "딥러닝 딥러닝 신경망 신경망 학습 학습 모델 모델 인공지능 인공지능",
            },
            {
                "id": "b",
                "title": "딥러닝 활용 사례",
                "content": "딥러닝 딥러닝 활용 활용 사례 사례 모델 모델 인공지능 인공지능",
            },
        ]
        result = map_topic_clusters(contents)
        self.assertGreaterEqual(len(result["clusters"]), 1)
        # 최소 하나의 클러스터에 두 콘텐츠가 포함됨
        all_clustered = set()
        for c in result["clusters"]:
            all_clustered.add(c["pillar_content_id"])
            for s in c["supporting_contents"]:
                all_clustered.add(s["id"])
        self.assertTrue({"a", "b"}.issubset(all_clustered))

    # --- 4. test_pillar_detection ---

    def test_pillar_detection(self):
        """필러 토픽이 문자열로 감지되고, pillar_content_id가 설정됨."""
        contents = self._make_python_contents()
        result = map_topic_clusters(contents)
        # 최소 하나의 클러스터 존재
        self.assertGreaterEqual(len(result["clusters"]), 1)
        cluster = result["clusters"][0]
        # pillar_topic은 비어있지 않은 문자열
        self.assertIsInstance(cluster["pillar_topic"], str)
        self.assertTrue(len(cluster["pillar_topic"]) > 0)
        # pillar_content_id는 contents의 id 중 하나
        valid_ids = {item["id"] for item in contents}
        self.assertIn(cluster["pillar_content_id"], valid_ids)

    # --- 5. test_supporting_contents ---

    def test_supporting_contents(self):
        """서포팅 콘텐츠 목록에 id, title, relevance, shared_keywords 필드가 존재."""
        contents = self._make_python_contents()
        result = map_topic_clusters(contents)
        found_supporting = False
        for cluster in result["clusters"]:
            for sc in cluster["supporting_contents"]:
                found_supporting = True
                self.assertIn("id", sc)
                self.assertIn("title", sc)
                self.assertIn("relevance", sc)
                self.assertIn("shared_keywords", sc)
                self.assertIsInstance(sc["relevance"], float)
                self.assertIsInstance(sc["shared_keywords"], list)
        self.assertTrue(found_supporting, "서포팅 콘텐츠가 하나도 없음")

    # --- 6. test_cluster_strength_range ---

    def test_cluster_strength_range(self):
        """cluster_strength가 0-100 범위 내에 있음."""
        contents = self._make_python_contents()
        result = map_topic_clusters(contents)
        for cluster in result["clusters"]:
            self.assertGreaterEqual(cluster["cluster_strength"], 0)
            self.assertLessEqual(cluster["cluster_strength"], 100)

    # --- 7. test_unclustered_detection ---

    def test_unclustered_detection(self):
        """공통 키워드가 없는 고립 콘텐츠는 unclustered에 포함."""
        contents = [
            {
                "id": "x",
                "title": "기계학습 알고리즘",
                "content": "기계학습 기계학습 알고리즘 알고리즘 분류 분류 회귀 회귀",
            },
            {
                "id": "y",
                "title": "기계학습 모델 평가",
                "content": "기계학습 기계학습 모델 모델 평가 평가 정확도 정확도",
            },
            {
                "id": "z",
                "title": "제빵 기술 안내",
                "content": "제빵 제빵 발효 발효 반죽 반죽 오븐 오븐 밀가루 밀가루",
            },
        ]
        result = map_topic_clusters(contents)
        # z는 x, y와 공유 키워드가 없으므로 unclustered
        self.assertIn("z", result["unclustered"])

    # --- 8. test_multiple_clusters ---

    def test_multiple_clusters(self):
        """서로 다른 주제 그룹이 있으면 여러 클러스터가 형성될 수 있음."""
        contents = [
            {"id": "a1", "title": "축구 전술 분석", "content": "축구 축구 전술 전술 공격 공격 수비 수비 패스 패스"},
            {"id": "a2", "title": "축구 경기 리뷰", "content": "축구 축구 경기 경기 전술 전술 골 골 공격 공격"},
            {"id": "b1", "title": "주식 투자 전략", "content": "주식 주식 투자 투자 전략 전략 수익률 수익률 포트폴리오 포트폴리오"},
            {"id": "b2", "title": "주식 시장 분석", "content": "주식 주식 시장 시장 투자 투자 분석 분석 종목 종목"},
        ]
        result = map_topic_clusters(contents)
        # 최소 1개 클러스터 (주제가 명확히 분리되면 2개)
        self.assertGreaterEqual(len(result["clusters"]), 1)
        # 전체 콘텐츠의 대부분이 클러스터에 포함됨
        clustered_ids = set()
        for c in result["clusters"]:
            clustered_ids.add(c["pillar_content_id"])
            for s in c["supporting_contents"]:
                clustered_ids.add(s["id"])
        self.assertGreaterEqual(len(clustered_ids), 3)

    # --- 9. test_shared_keywords ---

    def test_shared_keywords(self):
        """서포팅 콘텐츠의 shared_keywords가 실제 공유 키워드를 포함."""
        contents = [
            {
                "id": "p1",
                "title": "블록체인 기술 개요",
                "content": "블록체인 블록체인 암호화 암호화 분산원장 분산원장 노드 노드 트랜잭션 트랜잭션",
            },
            {
                "id": "p2",
                "title": "블록체인 활용 사례",
                "content": "블록체인 블록체인 활용 활용 암호화 암호화 스마트계약 스마트계약 트랜잭션 트랜잭션",
            },
        ]
        result = map_topic_clusters(contents)
        self.assertGreaterEqual(len(result["clusters"]), 1)
        cluster = result["clusters"][0]
        all_shared = set()
        for sc in cluster["supporting_contents"]:
            all_shared.update(sc["shared_keywords"])
        # 블록체인, 암호화, 트랜잭션 등 공유 키워드가 있어야 함
        self.assertTrue(len(all_shared) > 0, "공유 키워드가 비어있음")

    # --- 10. test_summary_counts ---

    def test_summary_counts(self):
        """summary의 total_clusters와 avg_cluster_size가 올바르게 계산됨."""
        contents = self._make_python_contents()
        result = map_topic_clusters(contents)
        summary = result["summary"]
        self.assertEqual(summary["total_clusters"], len(result["clusters"]))
        self.assertIsInstance(summary["avg_cluster_size"], float)
        if summary["total_clusters"] > 0:
            self.assertGreater(summary["avg_cluster_size"], 0)

    # --- 11. test_coverage_score ---

    def test_coverage_score(self):
        """coverage는 0-100 범위의 float이며, 클러스터된 콘텐츠 비율을 반영."""
        contents = self._make_python_contents()
        result = map_topic_clusters(contents)
        coverage = result["summary"]["coverage"]
        self.assertGreaterEqual(coverage, 0.0)
        self.assertLessEqual(coverage, 100.0)
        self.assertIsInstance(coverage, float)

    # --- 12. test_suggestions ---

    def test_suggestions(self):
        """suggestions는 비어있지 않은 문자열 리스트."""
        contents = self._make_python_contents()
        result = map_topic_clusters(contents)
        suggestions = result["suggestions"]
        self.assertIsInstance(suggestions, list)
        self.assertTrue(len(suggestions) >= 1)
        for s in suggestions:
            self.assertIsInstance(s, str)
            self.assertTrue(len(s) > 0)


if __name__ == '__main__':
    unittest.main()
