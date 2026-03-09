"""치료 저널 서비스 테스트"""
import unittest
from services.therapy_journal_service import (
    add_entry, analyze_journal, detect_mood_trend, suggest_prompts,
    JournalEntry, JournalAnalysis
)


class TestTherapyJournalService(unittest.TestCase):

    def setUp(self):
        self.entries = [
            JournalEntry('e1', '2026-03-01', '오늘 힘들었다', 'sad', 3, ['스트레스']),
            JournalEntry('e2', '2026-03-02', '좀 나아졌다', 'neutral', 5, ['회복']),
            JournalEntry('e3', '2026-03-03', '기분 좋은 날', 'happy', 8, ['운동', '회복']),
            JournalEntry('e4', '2026-03-04', '매우 좋았다', 'happy', 9, ['운동']),
        ]

    def test_add_entry_appends(self):
        result = add_entry([], '새 항목', 'happy', 7, ['태그'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].mood, 'happy')

    def test_add_entry_energy_clamped(self):
        result = add_entry([], '테스트', 'calm', 15, [])
        self.assertEqual(result[0].energy_level, 10)
        result2 = add_entry([], '테스트', 'calm', -5, [])
        self.assertEqual(result2[0].energy_level, 1)

    def test_add_entry_immutable(self):
        original = list(self.entries)
        add_entry(self.entries, '추가', 'neutral', 5, [])
        self.assertEqual(len(self.entries), len(original))

    def test_analyze_journal_mood_distribution(self):
        analysis = analyze_journal(self.entries)
        self.assertEqual(analysis.mood_distribution['happy'], 2)
        self.assertEqual(analysis.mood_distribution['sad'], 1)

    def test_analyze_journal_avg_energy(self):
        analysis = analyze_journal(self.entries)
        expected = (3 + 5 + 8 + 9) / 4
        self.assertAlmostEqual(analysis.avg_energy, expected, places=2)

    def test_analyze_journal_common_themes(self):
        analysis = analyze_journal(self.entries)
        # '회복'과 '운동'이 각 2회
        self.assertIn('회복', analysis.common_themes[:3])

    def test_analyze_empty(self):
        analysis = analyze_journal([])
        self.assertEqual(analysis.total_entries, 0)
        self.assertEqual(analysis.avg_energy, 0.0)
        self.assertEqual(analysis.trend, 'stable')

    def test_detect_mood_trend_improving(self):
        trend = detect_mood_trend(self.entries)
        self.assertEqual(trend, 'improving')

    def test_detect_mood_trend_declining(self):
        declining = [
            JournalEntry('e1', '2026-03-01', '', 'happy', 9, []),
            JournalEntry('e2', '2026-03-02', '', 'happy', 8, []),
            JournalEntry('e3', '2026-03-03', '', 'sad', 3, []),
            JournalEntry('e4', '2026-03-04', '', 'sad', 2, []),
        ]
        trend = detect_mood_trend(declining)
        self.assertEqual(trend, 'declining')

    def test_detect_mood_trend_stable(self):
        stable = [
            JournalEntry('e1', '2026-03-01', '', 'neutral', 5, []),
            JournalEntry('e2', '2026-03-02', '', 'neutral', 5, []),
        ]
        trend = detect_mood_trend(stable)
        self.assertEqual(trend, 'stable')

    def test_suggest_prompts_declining(self):
        analysis = JournalAnalysis(4, {}, 3.0, [], 'declining')
        prompts = suggest_prompts(analysis)
        self.assertGreater(len(prompts), 0)

    def test_suggest_prompts_high_energy(self):
        analysis = JournalAnalysis(4, {}, 8.0, [], 'stable')
        prompts = suggest_prompts(analysis)
        self.assertTrue(any('도전' in p for p in prompts))


if __name__ == '__main__':
    unittest.main()
