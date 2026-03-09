"""speaker_notes_service 단위 테스트"""
import unittest

from services.speaker_notes_service import (
    extract_speaker_notes,
    SpeakerNote,
    _detect_speakers,
    _count_words,
    _extract_key_points,
)


class TestExtractSpeakerNotes(unittest.TestCase):
    """extract_speaker_notes 함수 테스트"""

    def test_empty_transcript(self):
        """빈 자막은 빈 리스트 반환"""
        result = extract_speaker_notes('')
        self.assertEqual(result, [])

    def test_whitespace_only(self):
        """공백만 있는 자막도 빈 리스트 반환"""
        result = extract_speaker_notes('   \n\n  ')
        self.assertEqual(result, [])

    def test_bracket_speaker_pattern(self):
        """[화자] 패턴 인식"""
        transcript = '[Alice] 안녕하세요\n[Bob] 반갑습니다'
        result = extract_speaker_notes(transcript)
        names = [r.speaker for r in result]
        self.assertIn('Alice', names)
        self.assertIn('Bob', names)

    def test_colon_speaker_pattern(self):
        """화자: 패턴 인식"""
        transcript = '진행자: 오늘 주제를 소개합니다\n게스트: 감사합니다'
        result = extract_speaker_notes(transcript)
        names = [r.speaker for r in result]
        self.assertIn('진행자', names)
        self.assertIn('게스트', names)

    def test_paren_speaker_pattern(self):
        """(화자) 패턴 인식"""
        transcript = '(Host) Welcome to the show\n(Guest) Thank you'
        result = extract_speaker_notes(transcript)
        names = [r.speaker for r in result]
        self.assertIn('Host', names)
        self.assertIn('Guest', names)

    def test_predefined_speakers_fallback(self):
        """사전 지정 화자로 라인 분배"""
        transcript = '첫 번째 줄입니다\n두 번째 줄입니다\n세 번째 줄입니다'
        result = extract_speaker_notes(transcript, speakers=['A', 'B'])
        names = [r.speaker for r in result]
        self.assertIn('A', names)
        self.assertIn('B', names)

    def test_no_speaker_info_default(self):
        """화자 정보 없으면 기본 'Speaker' 사용"""
        transcript = '안녕하세요 여러분'
        result = extract_speaker_notes(transcript)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].speaker, 'Speaker')

    def test_word_count(self):
        """단어 수 정확히 계산"""
        transcript = '[Host] 하나 둘 셋 넷 다섯'
        result = extract_speaker_notes(transcript)
        host = [r for r in result if r.speaker == 'Host'][0]
        self.assertEqual(host.word_count, 5)

    def test_key_points_extraction(self):
        """핵심 포인트 키워드 추출"""
        transcript = '[Speaker] 핵심 포인트는 이것입니다\n[Speaker] 일반 발언입니다'
        result = extract_speaker_notes(transcript)
        speaker = result[0]
        self.assertGreater(len(speaker.key_points), 0)
        self.assertTrue(any('핵심' in kp for kp in speaker.key_points))

    def test_sorted_by_word_count_desc(self):
        """발언량 내림차순 정렬"""
        transcript = (
            '[A] 짧은 말\n'
            '[B] 이것은 상당히 긴 발언으로 여러 단어가 포함되어 있습니다'
        )
        result = extract_speaker_notes(transcript)
        if len(result) >= 2:
            self.assertGreaterEqual(result[0].word_count, result[1].word_count)

    def test_result_is_speaker_note_dataclass(self):
        """반환 타입이 SpeakerNote dataclass"""
        transcript = '[Host] 테스트 발언'
        result = extract_speaker_notes(transcript)
        self.assertIsInstance(result[0], SpeakerNote)

    def test_predefined_speakers_filter(self):
        """사전 지정 화자만 필터링 (패턴 매칭 시)"""
        transcript = '[Alice] 안녕\n[Bob] 반갑\n[Charlie] 하이'
        result = extract_speaker_notes(transcript, speakers=['Alice', 'Bob'])
        names = [r.speaker for r in result]
        self.assertIn('Alice', names)
        self.assertIn('Bob', names)
        self.assertNotIn('Charlie', names)


class TestHelperFunctions(unittest.TestCase):
    """헬퍼 함수 테스트"""

    def test_count_words_korean(self):
        """한국어 단어 수 계산"""
        self.assertEqual(_count_words('하나 둘 셋'), 3)

    def test_count_words_english(self):
        """영어 단어 수 계산"""
        self.assertEqual(_count_words('one two three'), 3)

    def test_count_words_empty(self):
        """빈 문자열 단어 수"""
        self.assertEqual(_count_words(''), 0)

    def test_extract_key_points_with_keywords(self):
        """키워드 포함 발언 추출"""
        notes = ['중요한 포인트입니다', '일반 발언', '결론은 이렇습니다']
        points = _extract_key_points(notes)
        self.assertEqual(len(points), 2)

    def test_extract_key_points_no_match(self):
        """키워드 없는 발언 — 빈 리스트"""
        notes = ['일반 발언입니다', '또 다른 발언']
        points = _extract_key_points(notes)
        self.assertEqual(len(points), 0)

    def test_extract_key_points_no_duplicates(self):
        """핵심 포인트 중복 방지"""
        notes = ['중요한 핵심 포인트']  # '중요한'과 '핵심' 모두 매칭
        points = _extract_key_points(notes)
        self.assertEqual(len(points), 1)


if __name__ == '__main__':
    unittest.main()
