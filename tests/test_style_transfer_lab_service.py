"""문체 전이 실험실 서비스 테스트"""
import unittest
from services.style_transfer_lab_service import (
    define_style, transfer_style, analyze_style, compare_styles,
    StyleProfile, TransferResult
)


class TestStyleTransferLabService(unittest.TestCase):

    def setUp(self):
        self.formal = define_style('격식체', 0.9, 0.7, 0.1, ['입니다', '합니다'])
        self.casual = define_style('비격식체', 0.2, 0.3, 0.8, ['야', '거야'])

    def test_define_style(self):
        self.assertIsInstance(self.formal, StyleProfile)
        self.assertEqual(self.formal.name, '격식체')
        self.assertEqual(self.formal.characteristics['formality'], 0.9)

    def test_define_style_clamped(self):
        s = define_style('극단', 1.5, -0.5, 2.0, [])
        self.assertEqual(s.characteristics['formality'], 1.0)
        self.assertEqual(s.characteristics['complexity'], 0.0)
        self.assertEqual(s.characteristics['emotion'], 1.0)

    def test_transfer_to_formal(self):
        result = transfer_style('나 오늘 좋았어', self.casual, self.formal)
        self.assertIsInstance(result, TransferResult)
        self.assertEqual(result.source_style, '비격식체')
        self.assertEqual(result.target_style, '격식체')

    def test_transfer_changes_text(self):
        # casual→formal 변환 시 '나' → '저' 등
        result = transfer_style('나는 했어', self.casual, self.formal)
        self.assertIn('저', result.transferred)

    def test_transfer_similarity_range(self):
        result = transfer_style('테스트 문장입니다', self.formal, self.casual)
        self.assertGreaterEqual(result.similarity, 0.0)
        self.assertLessEqual(result.similarity, 1.0)

    def test_analyze_style_formal_text(self):
        profile = analyze_style('이것은 중요한 사안입니다. 검토가 필요합니다. 확인하겠습니다.')
        self.assertIsInstance(profile, StyleProfile)
        self.assertGreater(profile.characteristics['formality'], 0)

    def test_analyze_style_emotional_text(self):
        profile = analyze_style('와!! 정말 좋다~ ㅋㅋㅋ 대박!!!')
        self.assertGreater(profile.characteristics['emotion'], 0)

    def test_compare_styles(self):
        result = compare_styles(self.formal, self.casual)
        self.assertIn('formality', result)
        self.assertIn('overall_similarity', result)
        self.assertLessEqual(result['overall_similarity'], 1.0)

    def test_compare_identical_styles(self):
        result = compare_styles(self.formal, self.formal)
        self.assertEqual(result['formality']['diff'], 0.0)
        self.assertEqual(result['overall_similarity'], 1.0)

    def test_transfer_same_style_minimal_change(self):
        result = transfer_style('테스트', self.formal, self.formal)
        self.assertGreater(result.similarity, 0.5)


if __name__ == '__main__':
    unittest.main()
