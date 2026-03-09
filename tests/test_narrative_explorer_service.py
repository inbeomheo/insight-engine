"""Narrative Explorer Service 테스트 — 15개 이상."""

import unittest
from services.narrative_explorer_service import (
    Narrative,
    explore_narratives,
    _split_sentences,
    _count_keyword_hits,
    _detect_sentiment,
    _detect_angles,
    _find_evidence,
    _ensure_minimum_narratives,
)


class TestSplitSentences(unittest.TestCase):
    """문장 분리 헬퍼 테스트."""

    def test_period_split(self):
        text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        result = _split_sentences(text)
        self.assertEqual(len(result), 3)

    def test_newline_split(self):
        text = "첫 번째 줄\n두 번째 줄\n세 번째 줄"
        result = _split_sentences(text)
        self.assertEqual(len(result), 3)

    def test_short_fragments_filtered(self):
        """5자 미만 조각은 필터링된다."""
        text = "긴 문장입니다. AB. 또 다른 긴 문장이에요."
        result = _split_sentences(text)
        self.assertTrue(all(len(s) >= 5 for s in result))

    def test_empty_string(self):
        result = _split_sentences("")
        self.assertEqual(result, [])


class TestCountKeywordHits(unittest.TestCase):
    """키워드 카운팅 테스트."""

    def test_basic_count(self):
        text = "비용 절감과 비용 최적화가 중요합니다"
        hits = _count_keyword_hits(text, ["비용"])
        self.assertEqual(hits, 2)

    def test_case_insensitive(self):
        text = "AI and ai are both important for ML"
        hits = _count_keyword_hits(text, ["ai", "ml"])
        self.assertEqual(hits, 3)  # AI, ai, ML

    def test_no_hits(self):
        text = "오늘 날씨가 좋습니다"
        hits = _count_keyword_hits(text, ["기술", "혁신"])
        self.assertEqual(hits, 0)


class TestDetectSentiment(unittest.TestCase):
    """감성 감지 테스트."""

    def test_positive_sentiment(self):
        text = "이 서비스는 좋은 장점이 많고 효율적이며 유용합니다"
        sentiment, score = _detect_sentiment(text)
        self.assertEqual(sentiment, "positive")
        self.assertGreater(score, 0.5)

    def test_negative_sentiment(self):
        text = "이 제품은 문제가 많고 불편하며 실망스럽습니다"
        sentiment, score = _detect_sentiment(text)
        self.assertEqual(sentiment, "negative")
        self.assertGreater(score, 0.5)

    def test_neutral_sentiment(self):
        text = "오늘 점심은 김밥이었습니다"
        sentiment, score = _detect_sentiment(text)
        self.assertEqual(sentiment, "neutral")

    def test_score_range(self):
        """강도 점수는 항상 0~1 사이."""
        for text in ["좋은 좋은 좋은 좋은", "문제 위험 실패 문제", "일반 텍스트"]:
            _, score = _detect_sentiment(text)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


class TestDetectAngles(unittest.TestCase):
    """앵글 감지 테스트."""

    def test_tech_angle(self):
        text = "AI 기술 혁신과 디지털 플랫폼 자동화 기술"
        angles = _detect_angles(text)
        labels = [a[0] for a in angles]
        self.assertIn("기술/혁신", labels)

    def test_cost_angle(self):
        text = "비용 절감과 예산 관리, 투자 수익률이 핵심입니다"
        angles = _detect_angles(text)
        labels = [a[0] for a in angles]
        self.assertIn("비용/경제성", labels)

    def test_multiple_angles(self):
        text = "AI 기술로 비용을 절감하고 사용자 경험을 개선합니다"
        angles = _detect_angles(text)
        self.assertGreaterEqual(len(angles), 2)

    def test_sorted_by_hits(self):
        text = "기술 기술 기술 혁신 디지털. 비용."
        angles = _detect_angles(text)
        if len(angles) >= 2:
            self.assertGreaterEqual(angles[0][1], angles[1][1])


class TestFindEvidence(unittest.TestCase):
    """근거 문장 추출 테스트."""

    def test_finds_relevant_sentences(self):
        sentences = [
            "AI 기술이 비용을 절감합니다",
            "오늘 날씨가 좋습니다",
            "디지털 혁신은 좋은 결과를 만듭니다",
        ]
        evidence = _find_evidence(sentences, ["기술", "혁신"], ["좋은"])
        self.assertGreater(len(evidence), 0)
        # 관련 문장이 포함되어야 함
        self.assertTrue(any("기술" in e or "혁신" in e for e in evidence))

    def test_max_evidence_limit(self):
        sentences = [f"기술 관련 문장 {i}번" for i in range(10)]
        evidence = _find_evidence(sentences, ["기술"], ["좋은"], max_evidence=2)
        self.assertLessEqual(len(evidence), 2)


class TestEnsureMinimumNarratives(unittest.TestCase):
    """최소 내러티브 보장 테스트."""

    def test_fills_to_minimum(self):
        narratives = [
            Narrative(topic="테스트", angle="기술/혁신", sentiment="positive", strength=0.8),
        ]
        result = _ensure_minimum_narratives(narratives, "테스트", ["문장 하나"])
        self.assertGreaterEqual(len(result), 3)

    def test_no_fill_if_enough(self):
        narratives = [
            Narrative(topic="t", angle=f"앵글{i}", sentiment="neutral", strength=0.5)
            for i in range(5)
        ]
        result = _ensure_minimum_narratives(narratives, "t", ["문장"])
        self.assertEqual(len(result), 5)


class TestExploreNarratives(unittest.TestCase):
    """explore_narratives 통합 테스트."""

    def test_returns_at_least_3(self):
        """최소 3개 내러티브 반환."""
        result = explore_narratives("AI 자동화")
        self.assertGreaterEqual(len(result), 3)

    def test_all_narratives_valid(self):
        """모든 내러티브가 유효한 필드를 가진다."""
        result = explore_narratives("클라우드 비용", ["클라우드 비용 절감이 중요합니다"])
        for n in result:
            self.assertIsInstance(n, Narrative)
            self.assertTrue(n.topic)
            self.assertTrue(n.angle)
            self.assertIn(n.sentiment, ("positive", "negative", "neutral"))
            self.assertGreaterEqual(n.strength, 0.0)
            self.assertLessEqual(n.strength, 1.0)
            self.assertIsInstance(n.supporting_evidence, list)

    def test_sorted_by_strength(self):
        """strength 내림차순 정렬 확인."""
        sources = [
            "AI 기술 혁신으로 디지털 전환이 가속화되고 있습니다.",
            "비용 절감과 예산 효율화가 기업의 핵심 과제입니다.",
            "보안 위험과 개인정보 문제가 우려됩니다.",
            "사용자 경험 개선이 시장 경쟁력의 핵심입니다.",
        ]
        result = explore_narratives("디지털 전환", sources)
        for i in range(len(result) - 1):
            self.assertGreaterEqual(result[i].strength, result[i + 1].strength)

    def test_with_sources(self):
        """소스 텍스트를 제공했을 때 내러티브에 근거가 포함된다."""
        sources = [
            "AI 기술은 생산성을 크게 높여줍니다. 자동화로 효율이 증가합니다.",
            "하지만 비용 문제가 있고 보안 리스크도 걱정됩니다.",
        ]
        result = explore_narratives("AI 도입", sources)
        self.assertGreaterEqual(len(result), 3)
        # 최소 하나의 내러티브에 근거가 있어야 함
        has_evidence = any(len(n.supporting_evidence) > 0 for n in result)
        self.assertTrue(has_evidence)

    def test_no_sources(self):
        """소스 없이 topic만으로도 최소 3개 반환."""
        result = explore_narratives("원격 근무")
        self.assertGreaterEqual(len(result), 3)

    def test_empty_sources(self):
        """빈 소스 리스트도 처리된다."""
        result = explore_narratives("테스트 주제", [])
        self.assertGreaterEqual(len(result), 3)

    def test_rich_text_multiple_angles(self):
        """풍부한 텍스트에서 여러 앵글이 감지된다."""
        sources = [
            "AI 기술 혁신이 시장 트렌드를 바꾸고 있습니다.",
            "비용 절감과 투자 수익이 극대화됩니다.",
            "사용자 경험과 접근성이 향상되었습니다.",
            "환경과 지속가능한 발전을 위한 노력도 필요합니다.",
            "보안과 개인정보 보호에 대한 규제가 강화되고 있습니다.",
        ]
        result = explore_narratives("디지털 전환", sources)
        angles = {n.angle for n in result}
        # 최소 3개 이상의 서로 다른 앵글이 있어야 함
        self.assertGreaterEqual(len(angles), 3)


if __name__ == "__main__":
    unittest.main()
