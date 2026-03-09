"""soundstaging_service 단위 테스트"""
import unittest

from services.soundstaging_service import (
    design_soundstage,
    SoundstageDesign,
    SoundLayer,
    SUPPORTED_ENVIRONMENTS,
    _detect_additional_layers,
)


class TestDesignSoundstage(unittest.TestCase):
    """design_soundstage 함수 테스트"""

    def test_unsupported_environment(self):
        """지원하지 않는 환경 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            design_soundstage('script', environment='underwater')
        self.assertIn('underwater', str(ctx.exception))

    def test_empty_script_studio(self):
        """빈 스크립트 — 기본 레이어만 반환"""
        result = design_soundstage('', environment='studio')
        self.assertEqual(result.environment, 'studio')
        self.assertGreater(len(result.layers), 0)
        self.assertTrue(any('비어 있어' in n for n in result.spatial_notes))

    def test_studio_environment(self):
        """스튜디오 환경 기본 설정"""
        result = design_soundstage('대본입니다', environment='studio')
        self.assertEqual(result.environment, 'studio')
        layer_types = [l.type for l in result.layers]
        self.assertIn('voice', layer_types)

    def test_outdoor_environment(self):
        """야외 환경 설정"""
        result = design_soundstage('대본입니다', environment='outdoor')
        self.assertEqual(result.environment, 'outdoor')
        layer_names = [l.name for l in result.layers]
        self.assertTrue(any('Wind' in n or 'Nature' in n for n in layer_names))

    def test_stage_environment(self):
        """무대 환경 설정"""
        result = design_soundstage('대본입니다', environment='stage')
        self.assertEqual(result.environment, 'stage')
        layer_names = [l.name for l in result.layers]
        self.assertTrue(any('Audience' in n or 'Stage' in n for n in layer_names))

    def test_virtual_environment(self):
        """가상 환경 설정"""
        result = design_soundstage('대본입니다', environment='virtual')
        self.assertEqual(result.environment, 'virtual')
        layer_names = [l.name for l in result.layers]
        self.assertTrue(any('Digital' in n or 'UI' in n for n in layer_names))

    def test_keyword_adds_bgm_layer(self):
        """'음악' 키워드 → BGM 레이어 추가"""
        result = design_soundstage('배경음악을 추가합니다', environment='studio')
        layer_names = [l.name for l in result.layers]
        self.assertIn('Background Music', layer_names)

    def test_keyword_adds_narration_layer(self):
        """'나레이션' 키워드 → Narration 레이어 추가"""
        result = design_soundstage('나레이션이 필요합니다', environment='studio')
        layer_names = [l.name for l in result.layers]
        self.assertIn('Narration', layer_names)

    def test_keyword_adds_interview_layer(self):
        """'인터뷰' 키워드 → Guest Voice 레이어 추가"""
        result = design_soundstage('인터뷰 진행합니다', environment='studio')
        layer_names = [l.name for l in result.layers]
        self.assertIn('Guest Voice', layer_names)

    def test_no_duplicate_layers(self):
        """중복 레이어 방지"""
        result = design_soundstage('음악 음악 음악', environment='studio')
        layer_names = [l.name for l in result.layers]
        # Background Music이 1개만 있어야 함
        self.assertEqual(layer_names.count('Background Music'), 1)

    def test_result_is_dataclass(self):
        """반환 타입 확인"""
        result = design_soundstage('test', environment='studio')
        self.assertIsInstance(result, SoundstageDesign)

    def test_volume_range(self):
        """모든 레이어 볼륨 0~1 범위"""
        result = design_soundstage('음악 나레이션 인터뷰 효과음', environment='stage')
        for layer in result.layers:
            self.assertGreaterEqual(layer.volume, 0.0)
            self.assertLessEqual(layer.volume, 1.0)

    def test_spatial_notes_not_empty(self):
        """공간 노트가 비어있지 않음"""
        result = design_soundstage('내용', environment='studio')
        self.assertGreater(len(result.spatial_notes), 0)


class TestDetectAdditionalLayers(unittest.TestCase):
    """_detect_additional_layers 헬퍼 테스트"""

    def test_no_keywords(self):
        """키워드 없으면 빈 리스트"""
        result = _detect_additional_layers('일반 대본입니다')
        self.assertEqual(result, [])

    def test_multiple_keywords(self):
        """여러 키워드 동시 매칭"""
        result = _detect_additional_layers('음악과 효과음이 필요합니다')
        names = [l.name for l in result]
        self.assertIn('Background Music', names)
        self.assertIn('Sound Effects', names)

    def test_english_keywords(self):
        """영어 키워드 매칭"""
        result = _detect_additional_layers('add some bgm and sfx')
        names = [l.name for l in result]
        self.assertIn('Background Music', names)
        self.assertIn('Sound Effects', names)


if __name__ == '__main__':
    unittest.main()
