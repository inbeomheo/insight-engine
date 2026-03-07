"""Rhetorical Device Detector 서비스 테스트."""
import unittest
from services.rhetorical_device_detector_service import detect_rhetorical_devices


class TestRhetoricalDeviceDetector(unittest.TestCase):

    def test_empty_content(self):
        result = detect_rhetorical_devices('')
        self.assertEqual(result['summary']['total_devices'], 0)
        self.assertEqual(result['score'], 50.0)

    def test_none_content(self):
        result = detect_rhetorical_devices(None)
        self.assertEqual(result['summary']['total_devices'], 0)

    def test_simile_korean(self):
        content = '그의 눈은 별처럼 빛났습니다. 그녀는 바람같이 빠르게 달렸습니다.'
        result = detect_rhetorical_devices(content)
        types = result['summary'].get('device_breakdown', {})
        self.assertIn('simile', types)

    def test_simile_english(self):
        content = 'She runs like a deer through the forest. He was as quiet as a mouse.'
        result = detect_rhetorical_devices(content)
        types = result['summary'].get('device_breakdown', {})
        self.assertIn('simile', types)

    def test_hyperbole_korean(self):
        content = '세상에서 가장 아름다운 풍경이었습니다. 끝없는 대지가 펼쳐졌습니다.'
        result = detect_rhetorical_devices(content)
        types = result['summary'].get('device_breakdown', {})
        self.assertIn('hyperbole', types)

    def test_rhetorical_question(self):
        content = '우리는 정말 이대로 괜찮은 것일까요? 더 나은 방법은 없는 걸까요?'
        result = detect_rhetorical_devices(content)
        types = result['summary'].get('device_breakdown', {})
        self.assertIn('rhetorical_question', types)

    def test_antithesis_korean(self):
        content = '중요한 것은 결과가 아니라 과정입니다. 양이 아닌 질이 중요합니다.'
        result = detect_rhetorical_devices(content)
        types = result['summary'].get('device_breakdown', {})
        self.assertIn('antithesis', types)

    def test_enumeration(self):
        content = '첫째, 기획이 필요합니다. 둘째, 실행이 중요합니다. 셋째, 평가를 합니다.'
        result = detect_rhetorical_devices(content)
        types = result['summary'].get('device_breakdown', {})
        self.assertIn('enumeration', types)

    def test_no_devices(self):
        content = '오늘 날씨가 맑습니다. 기온이 올라갑니다. 습도가 낮습니다.'
        result = detect_rhetorical_devices(content)
        self.assertEqual(result['summary']['device_types'], 0)

    def test_multiple_device_types(self):
        content = ('그의 목소리는 천둥처럼 울렸습니다. '
                   '중요한 것은 속도가 아니라 방향입니다. '
                   '우리는 정말 준비가 된 걸까요?')
        result = detect_rhetorical_devices(content)
        self.assertGreaterEqual(result['summary']['device_types'], 2)

    def test_level_rich(self):
        content = ('그의 눈은 별처럼 빛났습니다. '
                   '끝없는 대지가 펼쳐졌습니다. '
                   '중요한 것은 결과가 아니라 과정입니다. '
                   '우리는 정말 준비가 되었을까요? '
                   '첫째, 기획합니다. 둘째, 실행합니다.')
        result = detect_rhetorical_devices(content)
        self.assertIn(result['summary']['level'], ('rich', 'moderate'))

    def test_score_range(self):
        content = '일반적인 텍스트입니다. 별다른 수사법이 없습니다.'
        result = detect_rhetorical_devices(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인을 위한 테스트 문장입니다.'
        result = detect_rhetorical_devices(content)
        self.assertIn('devices', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_devices', result['summary'])
        self.assertIn('device_types', result['summary'])
        self.assertIn('density', result['summary'])
        self.assertIn('level', result['summary'])

    def test_device_structure(self):
        content = '그녀는 꽃처럼 아름다웠습니다.'
        result = detect_rhetorical_devices(content)
        if result['devices']:
            for d in result['devices']:
                self.assertIn('type', d)
                self.assertIn('text', d)

    def test_max_30_devices(self):
        # 많은 설의법
        questions = '. '.join([f'우리는 정말 이것을 할 수 있을까요{i}?' for i in range(35)])
        result = detect_rhetorical_devices(questions)
        self.assertLessEqual(len(result['devices']), 30)


if __name__ == '__main__':
    unittest.main()
