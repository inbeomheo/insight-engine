"""tone_adjuster_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.content.tone_adjuster_service import (
    analyze_tone,
    adjust_tone,
    get_tone_list,
    SUPPORTED_TONES,
    _count_markers,
    _sentence_count,
)


class TestAnalyzeTone(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_tone('')
        self.assertEqual(result['primary_tone'], 'neutral')
        self.assertEqual(result['sentence_count'], 0)

    def test_none_content(self):
        result = analyze_tone(None)
        self.assertEqual(result['primary_tone'], 'neutral')

    def test_formal_tone(self):
        text = '본 보고서는 다음과 같은 결과를 도출하였습니다. 이에 따라 정책 변경이 필요합니다. 관련 사항을 검토해 주시기 바랍니다.'
        result = analyze_tone(text)
        self.assertEqual(result['primary_tone'], 'formal')
        self.assertGreater(result['scores']['formal'], 0)

    def test_casual_tone(self):
        text = '오늘 정말 좋은 거 발견했어요. 이거 완전 대박이에요. 여러분도 꼭 해보세요!'
        result = analyze_tone(text)
        self.assertIn(result['primary_tone'], ['casual', 'persuasive'])

    def test_persuasive_tone(self):
        text = '반드시 지금 바로 시작해야 합니다. 핵심은 빠른 실행입니다. 꼭 확인하세요.'
        result = analyze_tone(text)
        self.assertEqual(result['primary_tone'], 'persuasive')

    def test_scores_are_normalized(self):
        text = '이것은 테스트 문장입니다. 다양한 내용을 포함합니다.'
        result = analyze_tone(text)
        for tone, score in result['scores'].items():
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_details_structure(self):
        text = '테스트 내용입니다.'
        result = analyze_tone(text)
        for tone in SUPPORTED_TONES:
            self.assertIn(tone, result['details'])
            detail = result['details'][tone]
            self.assertIn('label', detail)
            self.assertIn('score', detail)
            self.assertIn('marker_count', detail)

    def test_char_count(self):
        text = '안녕하세요 테스트입니다.'
        result = analyze_tone(text)
        self.assertEqual(result['char_count'], len(text))

    def test_sentence_count(self):
        text = '첫 번째 문장입니다. 두 번째 문장입니다. 세 번째.'
        result = analyze_tone(text)
        self.assertGreaterEqual(result['sentence_count'], 2)


class TestCountMarkers(unittest.TestCase):

    def test_basic_count(self):
        self.assertEqual(_count_markers('습니다 입니다', ['습니다', '입니다']), 2)

    def test_empty_markers(self):
        self.assertEqual(_count_markers('아무 텍스트', []), 0)

    def test_no_match(self):
        self.assertEqual(_count_markers('hello world', ['습니다']), 0)

    def test_multiple_occurrences(self):
        self.assertEqual(_count_markers('습니다 습니다 습니다', ['습니다']), 3)


class TestSentenceCount(unittest.TestCase):

    def test_single_sentence(self):
        self.assertEqual(_sentence_count('문장 하나'), 1)

    def test_multiple_sentences(self):
        count = _sentence_count('첫째. 둘째. 셋째.')
        self.assertGreaterEqual(count, 2)

    def test_empty(self):
        self.assertEqual(_sentence_count(''), 1)


class TestAdjustTone(unittest.TestCase):

    @patch('services.content.tone_adjuster_service.ai_service')
    def test_adjust_to_formal(self, mock_ai):
        mock_ai.create_content.return_value = {'content': '본 결과를 보고합니다.'}
        result = adjust_tone('이거 완전 대박이에요!', 'formal', 'test-model')
        self.assertEqual(result['target_tone'], 'formal')
        self.assertIn('adjusted_content', result)
        self.assertGreater(result['char_count'], 0)

    @patch('services.content.tone_adjuster_service.ai_service')
    def test_adjust_to_casual(self, mock_ai):
        mock_ai.create_content.return_value = {'content': '이거 진짜 좋아요!'}
        result = adjust_tone('본 보고서는 다음과 같습니다.', 'casual', 'test-model')
        self.assertEqual(result['target_tone'], 'casual')

    def test_unsupported_tone(self):
        result = adjust_tone('테스트', 'robot', 'model')
        self.assertIn('error', result)

    def test_empty_content(self):
        result = adjust_tone('', 'formal', 'model')
        self.assertIn('error', result)

    def test_none_content(self):
        result = adjust_tone(None, 'formal', 'model')
        self.assertIn('error', result)

    @patch('services.content.tone_adjuster_service.ai_service')
    def test_tone_analysis_included(self, mock_ai):
        mock_ai.create_content.return_value = {'content': '조정된 텍스트입니다.'}
        result = adjust_tone('원본 텍스트', 'neutral', 'model')
        self.assertIn('tone_analysis', result)
        self.assertIn('original_tone', result)

    @patch('services.content.tone_adjuster_service.ai_service')
    def test_ai_failure_returns_error(self, mock_ai):
        mock_ai.create_content.side_effect = Exception('API 오류')
        result = adjust_tone('테스트', 'formal', 'model')
        self.assertIn('error', result)


class TestGetToneList(unittest.TestCase):

    def test_returns_all_tones(self):
        tones = get_tone_list()
        self.assertEqual(len(tones), len(SUPPORTED_TONES))
        for tone in tones:
            self.assertIn('id', tone)
            self.assertIn('label', tone)
            self.assertIn('description', tone)

    def test_tone_ids_match(self):
        ids = [t['id'] for t in get_tone_list()]
        self.assertEqual(set(ids), set(SUPPORTED_TONES))


if __name__ == '__main__':
    unittest.main()
