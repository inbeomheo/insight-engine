"""speaker_identification_service 단위 테스트"""
import unittest

from services.speaker_identification_service import (
    SpeakerCandidate,
    LabeledSegment,
    identify_speakers,
    _normalize_time,
    _time_to_seconds,
    _seconds_to_time,
    _parse_timestamped_lines,
    _match_speaker,
)


class TestNormalizeTime(unittest.TestCase):
    """_normalize_time 테스트"""

    def test_mm_ss(self):
        """MM:SS 형식 정규화"""
        self.assertEqual(_normalize_time('3:05'), '3:05')

    def test_hh_mm_ss(self):
        """HH:MM:SS 형식 정규화"""
        self.assertEqual(_normalize_time('1:02:30'), '1:02:30')

    def test_zero_hour_removed(self):
        """0시간은 MM:SS로 축소"""
        self.assertEqual(_normalize_time('0:05:30'), '5:30')


class TestTimeToSeconds(unittest.TestCase):
    """_time_to_seconds 테스트"""

    def test_mm_ss(self):
        self.assertEqual(_time_to_seconds('3:25'), 205)

    def test_hh_mm_ss(self):
        self.assertEqual(_time_to_seconds('1:02:30'), 3750)

    def test_zero(self):
        self.assertEqual(_time_to_seconds('0:00'), 0)

    def test_invalid_format(self):
        """잘못된 형식은 0 반환"""
        self.assertEqual(_time_to_seconds('invalid'), 0)


class TestSecondsToTime(unittest.TestCase):
    """_seconds_to_time 테스트"""

    def test_under_one_hour(self):
        self.assertEqual(_seconds_to_time(205), '3:25')

    def test_over_one_hour(self):
        self.assertEqual(_seconds_to_time(3750), '1:02:30')

    def test_zero(self):
        self.assertEqual(_seconds_to_time(0), '0:00')

    def test_exact_minute(self):
        self.assertEqual(_seconds_to_time(120), '2:00')


class TestParseTimestampedLines(unittest.TestCase):
    """_parse_timestamped_lines 테스트"""

    def test_basic_timestamps(self):
        """타임스탬프 기반 파싱"""
        transcript = '[0:00] 안녕하세요 [1:30] 오늘 주제는'
        result = _parse_timestamped_lines(transcript)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['start'], '0:00')
        self.assertEqual(result[0]['text'], '안녕하세요')
        self.assertEqual(result[1]['start'], '1:30')

    def test_no_timestamps(self):
        """타임스탬프 없으면 전체를 하나의 구간으로"""
        result = _parse_timestamped_lines('그냥 텍스트입니다')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['start'], '0:00')

    def test_empty_transcript(self):
        """빈 자막"""
        result = _parse_timestamped_lines('')
        self.assertEqual(result, [])

    def test_hh_mm_ss_format(self):
        """HH:MM:SS 형식 지원"""
        transcript = '[1:00:00] 1시간 지점 [1:05:30] 다음 내용'
        result = _parse_timestamped_lines(transcript)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['start'], '1:00:00')


class TestMatchSpeaker(unittest.TestCase):
    """_match_speaker 테스트"""

    def test_name_colon_pattern(self):
        """'이름:' 패턴으로 높은 신뢰도 매칭"""
        candidates = [SpeakerCandidate(name='김철수', keywords=['개발'])]
        speaker, confidence = _match_speaker('김철수: 오늘 발표를 시작하겠습니다', candidates)
        self.assertEqual(speaker, '김철수')
        self.assertGreaterEqual(confidence, 0.9)

    def test_keyword_matching(self):
        """키워드 기반 매칭"""
        candidates = [
            SpeakerCandidate(name='호스트', keywords=['진행', '소개', '오늘']),
            SpeakerCandidate(name='게스트', keywords=['연구', '논문', '실험']),
        ]
        speaker, confidence = _match_speaker('이 연구는 논문에서 발표된 실험 결과입니다', candidates)
        self.assertEqual(speaker, '게스트')
        self.assertGreater(confidence, 0.0)

    def test_no_candidates(self):
        """후보가 없으면 Unknown"""
        speaker, confidence = _match_speaker('아무 텍스트', [])
        self.assertEqual(speaker, 'Unknown')
        self.assertEqual(confidence, 0.0)

    def test_no_match(self):
        """매칭 실패 시 Unknown"""
        candidates = [SpeakerCandidate(name='화자A', keywords=['특정키워드'])]
        speaker, confidence = _match_speaker('관련 없는 텍스트', candidates)
        self.assertEqual(speaker, 'Unknown')
        self.assertEqual(confidence, 0.0)


class TestIdentifySpeakers(unittest.TestCase):
    """identify_speakers 통합 테스트"""

    def test_basic_identification(self):
        """기본 화자 식별"""
        transcript = '[0:00] 호스트: 안녕하세요 [0:30] 게스트: 반갑습니다'
        candidates = [
            {'name': '호스트', 'keywords': ['안녕', '소개']},
            {'name': '게스트', 'keywords': ['반갑', '감사']},
        ]
        result = identify_speakers(transcript, candidates)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], LabeledSegment)
        self.assertEqual(result[0].speaker, '호스트')
        self.assertEqual(result[1].speaker, '게스트')

    def test_empty_transcript(self):
        """빈 자막은 빈 리스트 반환"""
        result = identify_speakers('', [{'name': 'A', 'keywords': []}])
        self.assertEqual(result, [])

    def test_whitespace_only_transcript(self):
        """공백만 있는 자막"""
        result = identify_speakers('   \n  ', [{'name': 'A', 'keywords': []}])
        self.assertEqual(result, [])

    def test_no_candidates(self):
        """후보 없으면 모두 Unknown"""
        transcript = '[0:00] 첫 번째 발화 [1:00] 두 번째 발화'
        result = identify_speakers(transcript, [])
        self.assertEqual(len(result), 2)
        for seg in result:
            self.assertEqual(seg.speaker, 'Unknown')
            self.assertEqual(seg.confidence, 0.0)

    def test_none_candidates(self):
        """candidates가 None"""
        transcript = '[0:00] 발화 내용'
        result = identify_speakers(transcript, None)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].speaker, 'Unknown')

    def test_segment_times(self):
        """구간 시작/종료 시간 검증"""
        transcript = '[0:00] 첫 구간 [1:00] 두 번째 [2:00] 세 번째'
        result = identify_speakers(transcript, [])
        self.assertEqual(result[0].start_time, '0:00')
        self.assertEqual(result[0].end_time, '1:00')
        self.assertEqual(result[1].start_time, '1:00')
        self.assertEqual(result[1].end_time, '2:00')

    def test_last_segment_end_time(self):
        """마지막 구간은 시작 + 30초"""
        transcript = '[5:00] 마지막 발화'
        result = identify_speakers(transcript, [])
        self.assertEqual(result[0].start_time, '5:00')
        self.assertEqual(result[0].end_time, '5:30')

    def test_confidence_range(self):
        """신뢰도가 0.0~1.0 범위"""
        transcript = '[0:00] 호스트: 시작합니다 [1:00] 게스트: 네 감사합니다'
        candidates = [
            {'name': '호스트', 'keywords': ['시작', '진행']},
            {'name': '게스트', 'keywords': ['감사', '네']},
        ]
        result = identify_speakers(transcript, candidates)
        for seg in result:
            self.assertGreaterEqual(seg.confidence, 0.0)
            self.assertLessEqual(seg.confidence, 1.0)

    def test_speaker_label_removed_from_text(self):
        """'이름:' 라벨이 텍스트에서 제거됨"""
        transcript = '[0:00] 김철수: 안녕하세요 여러분'
        candidates = [{'name': '김철수', 'keywords': []}]
        result = identify_speakers(transcript, candidates)
        # "김철수: " 부분이 제거되어야 함
        self.assertNotIn('김철수:', result[0].text)
        self.assertIn('안녕하세요', result[0].text)

    def test_keyword_based_identification(self):
        """키워드 기반 화자 식별 (이름 패턴 없이)"""
        transcript = '[0:00] 코드 리뷰를 시작하겠습니다 프로그래밍 [1:00] 이 디자인은 색상이 아름답습니다'
        candidates = [
            {'name': '개발자', 'keywords': ['코드', '프로그래밍', '리뷰']},
            {'name': '디자이너', 'keywords': ['디자인', '색상', '아름답']},
        ]
        result = identify_speakers(transcript, candidates)
        self.assertEqual(result[0].speaker, '개발자')
        self.assertEqual(result[1].speaker, '디자이너')

    def test_transcript_without_timestamps(self):
        """타임스탬프 없는 자막도 처리"""
        transcript = '안녕하세요 반갑습니다'
        candidates = [{'name': '화자', 'keywords': ['안녕']}]
        result = identify_speakers(transcript, candidates)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].start_time, '0:00')


if __name__ == '__main__':
    unittest.main()
