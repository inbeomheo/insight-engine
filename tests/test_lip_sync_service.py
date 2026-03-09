"""재더빙 립싱크 서비스 테스트"""
import unittest
from services.lip_sync_service import (
    generate_phonemes, map_mouth_shapes, create_track, validate_sync,
    LipSyncSegment, LipSyncTrack
)


class TestLipSyncService(unittest.TestCase):

    def test_generate_phonemes_korean(self):
        phonemes = generate_phonemes('한', 'ko')
        # '한' = ㅎ + ㅏ + ㄴ
        self.assertEqual(len(phonemes), 3)
        self.assertIn('ㅎ', phonemes)
        self.assertIn('ㅏ', phonemes)
        self.assertIn('ㄴ', phonemes)

    def test_generate_phonemes_korean_no_final(self):
        phonemes = generate_phonemes('가', 'ko')
        # '가' = ㄱ + ㅏ (종성 없음)
        self.assertEqual(len(phonemes), 2)

    def test_generate_phonemes_english(self):
        phonemes = generate_phonemes('hi', 'en')
        self.assertEqual(phonemes, ['h', 'i'])

    def test_generate_phonemes_english_space(self):
        phonemes = generate_phonemes('a b', 'en')
        self.assertIn('_', phonemes)

    def test_map_mouth_shapes(self):
        shapes = map_mouth_shapes(['ㅏ', 'ㅣ', 'ㅜ'])
        self.assertEqual(shapes, ['A', 'I', 'U'])

    def test_map_mouth_shapes_unknown(self):
        shapes = map_mouth_shapes(['ㄱ', 'ㄴ'])
        self.assertEqual(shapes, ['etc', 'etc'])

    def test_create_track(self):
        track = create_track('안녕하세요. 반갑습니다.', 'ko', 5.0)
        self.assertIsInstance(track, LipSyncTrack)
        self.assertEqual(track.language, 'ko')
        self.assertEqual(track.total_duration, 5.0)
        self.assertEqual(len(track.segments), 2)

    def test_create_track_segment_timing(self):
        track = create_track('첫 문장. 두번째 문장.', 'ko', 10.0)
        self.assertAlmostEqual(track.segments[0].start_time, 0.0)
        self.assertAlmostEqual(track.segments[0].end_time, 5.0)
        self.assertAlmostEqual(track.segments[1].start_time, 5.0)

    def test_create_track_empty_text(self):
        track = create_track('', 'ko', 5.0)
        self.assertEqual(len(track.segments), 0)

    def test_validate_sync_no_errors(self):
        track = create_track('문장 하나. 문장 둘.', 'ko', 4.0)
        errors = validate_sync(track)
        self.assertEqual(len(errors), 0)

    def test_validate_sync_overlap(self):
        seg1 = LipSyncSegment('s1', 0.0, 3.0, [], [], 'a')
        seg2 = LipSyncSegment('s2', 2.0, 5.0, [], [], 'b')
        track = LipSyncTrack('t1', 'ko', [seg1, seg2], 5.0)
        errors = validate_sync(track)
        overlap_errors = [e for e in errors if '겹침' in e]
        self.assertGreater(len(overlap_errors), 0)

    def test_validate_sync_exceeds_duration(self):
        seg = LipSyncSegment('s1', 0.0, 10.0, [], [], 'a')
        track = LipSyncTrack('t1', 'ko', [seg], 5.0)
        errors = validate_sync(track)
        exceed_errors = [e for e in errors if '초과' in e]
        self.assertGreater(len(exceed_errors), 0)


if __name__ == '__main__':
    unittest.main()
