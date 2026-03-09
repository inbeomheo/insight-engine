"""segment_version_service 단위 테스트"""
import unittest

from services.segment_version_service import (
    SegmentConfig,
    SEGMENT_PRESETS,
    generate_versions,
    get_segment_config,
    list_segments,
    register_custom_segment,
    _custom_segments,
)


class TestGenerateVersionsDefault(unittest.TestCase):
    """기본 3세그먼트 생성"""

    def test_generate_versions_default(self):
        """segments 미지정 시 기본 3개 프리셋으로 생성"""
        content = "AI 기술의 발전은 산업 전반에 변화를 가져오고 있다. " * 20
        result = generate_versions(content)

        self.assertEqual(set(result.keys()), {"beginner", "practitioner", "executive"})
        for seg_name, text in result.items():
            self.assertIsInstance(text, str)
            self.assertTrue(len(text) > 0)


class TestGenerateVersionsCustom(unittest.TestCase):
    """지정 세그먼트 생성"""

    def test_generate_versions_custom(self):
        """특정 세그먼트만 지정하여 생성"""
        content = "머신러닝 모델 학습 방법을 설명합니다. " * 10
        result = generate_versions(content, segments=["beginner", "executive"])

        self.assertEqual(set(result.keys()), {"beginner", "executive"})
        self.assertNotIn("practitioner", result)


class TestGenerateVersionsSingle(unittest.TestCase):
    """단일 세그먼트 생성"""

    def test_generate_versions_single(self):
        """단일 세그먼트만 지정"""
        content = "데이터 분석 기초 과정입니다."
        result = generate_versions(content, segments=["practitioner"])

        self.assertEqual(list(result.keys()), ["practitioner"])
        self.assertIn("[practitioner]", result["practitioner"])


class TestGetSegmentConfig(unittest.TestCase):
    """프리셋 조회"""

    def test_get_segment_config(self):
        """기본 프리셋 정상 조회"""
        config = get_segment_config("beginner")

        self.assertIsInstance(config, SegmentConfig)
        self.assertEqual(config.name, "beginner")
        self.assertEqual(config.tone, "친근한")
        self.assertEqual(config.max_length, 1500)
        self.assertEqual(config.focus, "기초 설명")
        self.assertEqual(config.cta_style, "학습 유도")

    def test_get_all_presets(self):
        """기본 프리셋 3개 모두 조회 가능"""
        for name in ["beginner", "practitioner", "executive"]:
            config = get_segment_config(name)
            self.assertEqual(config.name, name)


class TestGetSegmentConfigUnknown(unittest.TestCase):
    """없는 세그먼트 조회"""

    def test_get_segment_config_unknown(self):
        """존재하지 않는 세그먼트 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            get_segment_config("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))


class TestRegisterCustomSegment(unittest.TestCase):
    """커스텀 세그먼트 등록"""

    def setUp(self):
        _custom_segments.clear()

    def tearDown(self):
        _custom_segments.clear()

    def test_register_custom_segment(self):
        """커스텀 세그먼트 정상 등록"""
        config = register_custom_segment(
            name="marketer",
            tone="설득력 있는",
            max_length=1200,
            focus="마케팅 활용",
            cta_style="전환 유도",
        )

        self.assertIsInstance(config, SegmentConfig)
        self.assertEqual(config.name, "marketer")
        self.assertEqual(config.tone, "설득력 있는")

        # 조회 가능해야 함
        retrieved = get_segment_config("marketer")
        self.assertEqual(retrieved.name, "marketer")

    def test_register_empty_name_raises(self):
        """빈 이름 → ValueError"""
        with self.assertRaises(ValueError):
            register_custom_segment("", "톤", 100, "포커스", "CTA")

    def test_register_invalid_max_length_raises(self):
        """max_length 0 이하 → ValueError"""
        with self.assertRaises(ValueError):
            register_custom_segment("test", "톤", 0, "포커스", "CTA")

    def test_register_and_generate(self):
        """커스텀 세그먼트 등록 후 생성에 사용"""
        register_custom_segment("dev", "캐주얼", 500, "코드 예시", "깃헙 링크")
        content = "파이썬 비동기 프로그래밍 입문 가이드입니다."
        result = generate_versions(content, segments=["dev"])

        self.assertIn("dev", result)
        self.assertIn("[dev]", result["dev"])


class TestListSegments(unittest.TestCase):
    """세그먼트 목록 조회"""

    def setUp(self):
        _custom_segments.clear()

    def tearDown(self):
        _custom_segments.clear()

    def test_list_segments(self):
        """기본 프리셋 3개 포함"""
        segments = list_segments()

        self.assertIn("beginner", segments)
        self.assertIn("practitioner", segments)
        self.assertIn("executive", segments)

    def test_list_segments_with_custom(self):
        """커스텀 등록 후 목록에 포함"""
        register_custom_segment("analyst", "분석적", 1000, "데이터 해석", "대시보드 연결")
        segments = list_segments()

        self.assertIn("analyst", segments)
        self.assertGreaterEqual(len(segments), 4)

    def test_list_segments_sorted(self):
        """목록은 정렬되어 반환"""
        segments = list_segments()
        self.assertEqual(segments, sorted(segments))


class TestGenerateVersionsEmptyContent(unittest.TestCase):
    """빈 콘텐츠 처리"""

    def test_generate_versions_empty_content(self):
        """빈 문자열 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            generate_versions("")
        self.assertIn("비어", str(ctx.exception))

    def test_generate_versions_whitespace_only(self):
        """공백만 있는 콘텐츠 → ValueError"""
        with self.assertRaises(ValueError):
            generate_versions("   \n\t  ")


class TestSegmentTransformOutput(unittest.TestCase):
    """변환 결과 형식 검증"""

    def test_output_contains_segment_metadata(self):
        """출력에 세그먼트 메타데이터 포함"""
        content = "클라우드 컴퓨팅 개요입니다."
        result = generate_versions(content, segments=["executive"])
        text = result["executive"]

        self.assertIn("[executive]", text)
        self.assertIn("간결한", text)
        self.assertIn("의사결정 요약", text)

    def test_output_respects_max_length(self):
        """출력이 max_length를 초과하지 않음"""
        content = "가" * 5000
        result = generate_versions(content, segments=["executive"])  # max_length=800
        text = result["executive"]

        self.assertLessEqual(len(text), 800)

    def test_unknown_segment_in_list_raises(self):
        """segments 목록에 없는 세그먼트 → ValueError"""
        with self.assertRaises(ValueError):
            generate_versions("콘텐츠", segments=["ghost"])


if __name__ == "__main__":
    unittest.main()
