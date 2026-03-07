"""passive_voice_service 단위 테스트"""
import unittest

from services.passive_voice_service import (
    detect_passive,
)


class TestDetectPassive(unittest.TestCase):

    def test_empty_content(self):
        result = detect_passive('')
        self.assertEqual(result['score'], 100)
        self.assertEqual(result['passive_expressions'], [])

    def test_none_content(self):
        result = detect_passive(None)
        self.assertEqual(result['score'], 100)

    def test_active_content(self):
        result = detect_passive('개발자가 코드를 작성합니다. 팀이 프로젝트를 진행합니다.')
        self.assertEqual(len(result['passive_expressions']), 0)
        self.assertEqual(result['score'], 100)

    def test_passive_detected(self):
        result = detect_passive('코드가 작성되었습니다. 프로젝트가 완료되었습니다.')
        self.assertGreater(len(result['passive_expressions']), 0)

    def test_passive_keywords(self):
        content = '이 기능은 사용되고 있습니다. 데이터가 처리되었습니다.'
        result = detect_passive(content)
        self.assertGreater(result['summary']['total'], 0)

    def test_passive_ratio(self):
        content = '코드가 작성되었습니다. 기능이 개발되었습니다. 테스트가 완료되었습니다. 배포가 진행되었습니다.'
        result = detect_passive(content)
        self.assertGreater(result['summary']['passive_ratio'], 0)

    def test_suggestion_provided(self):
        result = detect_passive('API가 사용되고 있습니다.')
        if result['passive_expressions']:
            self.assertIn('suggestion', result['passive_expressions'][0])

    def test_score_decreases_with_passive(self):
        active = detect_passive('개발자가 코드를 작성합니다.')
        passive = detect_passive('코드가 작성되었습니다. 기능이 개발되었습니다. 테스트가 완료되었습니다.')
        self.assertGreaterEqual(active['score'], passive['score'])

    def test_score_bounded(self):
        result = detect_passive('테스트 콘텐츠입니다.')
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_suggestions_exist(self):
        result = detect_passive('많은 것이 변환되었습니다.')
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)

    def test_mixed_content(self):
        content = '개발자가 API를 설계합니다. 하지만 테스트는 자동으로 완료되었습니다.'
        result = detect_passive(content)
        # 피동과 능동이 섞여 있을 때
        self.assertLess(result['summary']['passive_ratio'], 100)


if __name__ == '__main__':
    unittest.main()
