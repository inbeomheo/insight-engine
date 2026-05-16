"""localization_checker_service 단위 테스트"""
import unittest
from services.content.localization_checker_service import check_localization


class TestCheckLocalization(unittest.TestCase):

    def test_empty(self):
        result = check_localization('')
        self.assertEqual(result['score'], 1.0)
        self.assertTrue(result['ready_for_localization'])

    def test_none(self):
        result = check_localization(None)
        self.assertEqual(result['score'], 1.0)

    def test_date_detection(self):
        text = '이 글은 2026년 4월 17일에 작성되었습니다.'
        result = check_localization(text)
        self.assertGreater(result['summary']['dates'], 0)
        self.assertTrue(any(f['category'] == 'date' for f in result['findings']))

    def test_date_dot_format(self):
        text = '출시일: 2026.04.17'
        result = check_localization(text)
        self.assertGreater(result['summary']['dates'], 0)

    def test_currency_detection(self):
        text = '가격은 50,000원입니다. 해외가: $49.99'
        result = check_localization(text)
        self.assertGreater(result['summary']['currencies'], 0)

    def test_cultural_reference(self):
        text = '설날과 추석은 한국의 대표적인 명절입니다.'
        result = check_localization(text)
        self.assertGreater(result['summary']['cultural_refs'], 0)
        self.assertFalse(result['ready_for_localization'])

    def test_phone_format(self):
        text = '연락처: 010-1234-5678'
        result = check_localization(text)
        self.assertGreater(result['summary']['cultural_refs'], 0)

    def test_clean_content(self):
        text = 'AI 기술은 빠르게 발전하고 있습니다. 데이터 분석이 핵심입니다.'
        result = check_localization(text)
        self.assertGreaterEqual(result['score'], 0.8)

    def test_target_locales(self):
        result = check_localization('내용', target_locales=['en', 'ja'])
        self.assertEqual(result['target_locales'], ['en', 'ja'])

    def test_score_range(self):
        text = '2026년 1월 1일에 50,000원짜리 김치를 샀습니다.'
        result = check_localization(text)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 1.0)

    def test_findings_max_limit(self):
        # 많은 이슈가 있어도 최대 20개만 반환
        text = '\n'.join([f'2026년 {i}월 1일' for i in range(1, 13)]) + '\n' + '\n'.join([f'{i},000원' for i in range(1, 20)])
        result = check_localization(text)
        self.assertLessEqual(len(result['findings']), 20)


if __name__ == '__main__':
    unittest.main()
