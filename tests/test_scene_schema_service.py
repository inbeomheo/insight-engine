"""
장면 스키마 서비스 테스트
"""

import unittest

from services.scene_schema_service import (
    SceneSchema,
    classify_scene_type,
    extract_schema,
    build_sequence,
    analyze_pacing,
)


class TestClassifySceneType(unittest.TestCase):
    """장면 유형 분류 테스트"""

    def test_classify_intro(self):
        """인트로 분류"""
        self.assertEqual(classify_scene_type("안녕하세요 오늘 소개할 내용은"), "intro")
        self.assertEqual(classify_scene_type("Welcome to this video"), "intro")

    def test_classify_conclusion(self):
        """결론 분류"""
        self.assertEqual(classify_scene_type("결론적으로 정리하면"), "conclusion")
        self.assertEqual(classify_scene_type("In summary, to wrap up"), "conclusion")

    def test_classify_climax(self):
        """클라이맥스 분류"""
        self.assertEqual(classify_scene_type("가장 핵심적인 비밀은"), "climax")

    def test_classify_transition(self):
        """전환 분류"""
        self.assertEqual(classify_scene_type("다음으로 넘어가서"), "transition")

    def test_classify_exposition(self):
        """설명 분류"""
        self.assertEqual(classify_scene_type("이 개념의 정의는 다음과 같습니다"), "exposition")

    def test_classify_empty(self):
        """빈 텍스트 — 기본값 exposition"""
        self.assertEqual(classify_scene_type(""), "exposition")

    def test_classify_no_keywords(self):
        """키워드 없는 텍스트"""
        self.assertEqual(classify_scene_type("고양이가 낮잠을 잡니다"), "exposition")


class TestExtractSchema(unittest.TestCase):
    """스키마 추출 테스트"""

    def test_extract_basic(self):
        """기본 스키마 추출"""
        schema = extract_schema("안녕하세요, 오늘 소개할 내용은 프로그래밍입니다.", 10.0)
        self.assertEqual(schema.scene_type, "intro")
        self.assertEqual(schema.duration_sec, 10.0)
        self.assertNotEqual(schema.scene_id, "")

    def test_extract_with_dialogue(self):
        """대화 추출 (따옴표)"""
        schema = extract_schema('"이것은 중요한 포인트입니다" 라고 전문가가 말했다.', 20.0)
        self.assertGreater(len(schema.key_dialogue), 0)

    def test_extract_emotion(self):
        """감정 감지"""
        schema = extract_schema("정말 신나는 소식입니다! 흥미로운 발견!", 5.0)
        self.assertEqual(schema.emotion, "excited")

    def test_extract_empty(self):
        """빈 세그먼트"""
        schema = extract_schema("", 0.0)
        self.assertEqual(schema.scene_type, "exposition")
        self.assertEqual(schema.key_dialogue, [])

    def test_extract_neutral_emotion(self):
        """중립 감정"""
        schema = extract_schema("오늘 날씨가 맑습니다.", 5.0)
        self.assertEqual(schema.emotion, "neutral")

    def test_extract_serious_emotion(self):
        """심각한 감정"""
        schema = extract_schema("이것은 매우 심각하고 중요한 문제입니다.", 15.0)
        self.assertEqual(schema.emotion, "serious")


class TestBuildSequence(unittest.TestCase):
    """장면 시퀀스 빌드 테스트"""

    def setUp(self):
        self.schemas = [
            SceneSchema("s1", "intro", emotion="excited", duration_sec=30),
            SceneSchema("s2", "exposition", emotion="calm", duration_sec=120),
            SceneSchema("s3", "climax", emotion="excited", duration_sec=60),
            SceneSchema("s4", "conclusion", emotion="calm", duration_sec=30),
        ]

    def test_sequence_length(self):
        """시퀀스 길이"""
        seq = build_sequence(self.schemas)
        self.assertEqual(len(seq), 4)

    def test_first_entry_no_transition(self):
        """첫 항목은 전환 없음"""
        seq = build_sequence(self.schemas)
        self.assertIsNone(seq[0]["transition_from"])
        self.assertFalse(seq[0]["type_changed"])

    def test_transition_detected(self):
        """유형 전환 감지"""
        seq = build_sequence(self.schemas)
        self.assertTrue(seq[1]["type_changed"])
        self.assertEqual(seq[1]["transition_from"], "intro")

    def test_emotion_change_detected(self):
        """감정 변화 감지"""
        seq = build_sequence(self.schemas)
        self.assertTrue(seq[1]["emotion_changed"])  # excited → calm

    def test_empty_sequence(self):
        """빈 시퀀스"""
        seq = build_sequence([])
        self.assertEqual(seq, [])

    def test_single_scene(self):
        """단일 장면"""
        seq = build_sequence([self.schemas[0]])
        self.assertEqual(len(seq), 1)


class TestAnalyzePacing(unittest.TestCase):
    """페이싱 분석 테스트"""

    def setUp(self):
        self.schemas = [
            SceneSchema("s1", "intro", duration_sec=30),
            SceneSchema("s2", "exposition", duration_sec=120),
            SceneSchema("s3", "exposition", duration_sec=90),
            SceneSchema("s4", "climax", duration_sec=60),
            SceneSchema("s5", "conclusion", duration_sec=30),
        ]

    def test_total_scenes(self):
        """총 장면 수"""
        result = analyze_pacing(self.schemas)
        self.assertEqual(result["total_scenes"], 5)

    def test_type_distribution(self):
        """유형별 비율"""
        result = analyze_pacing(self.schemas)
        dist = result["type_distribution"]
        self.assertAlmostEqual(dist["exposition"], 0.4)  # 2/5
        self.assertAlmostEqual(dist["intro"], 0.2)  # 1/5

    def test_avg_duration(self):
        """평균 길이"""
        result = analyze_pacing(self.schemas)
        expected_avg = (30 + 120 + 90 + 60 + 30) / 5
        self.assertAlmostEqual(result["avg_duration"], expected_avg)

    def test_type_avg_duration(self):
        """유형별 평균 길이"""
        result = analyze_pacing(self.schemas)
        self.assertAlmostEqual(result["type_avg_duration"]["exposition"], 105.0)

    def test_empty_pacing(self):
        """빈 장면 목록"""
        result = analyze_pacing([])
        self.assertEqual(result["total_scenes"], 0)
        self.assertEqual(result["type_distribution"], {})

    def test_single_scene_pacing(self):
        """단일 장면 페이싱"""
        result = analyze_pacing([SceneSchema("s1", "intro", duration_sec=60)])
        self.assertEqual(result["total_scenes"], 1)
        self.assertAlmostEqual(result["type_distribution"]["intro"], 1.0)


if __name__ == "__main__":
    unittest.main()
