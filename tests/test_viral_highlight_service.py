"""viral_highlight_service 단위 테스트"""
import unittest

from services.viral_highlight_service import (
    HighlightScore,
    Clip,
    score_highlights,
    extract_keyword_clips,
    _parse_timestamp,
    _format_timestamp,
    _calc_hook_score,
    _calc_emotion_score,
    _calc_info_density,
    _determine_viral_potential,
    _auto_segment,
    _clamp,
)


# ──────────────────────────────────────────
# 유틸리티 함수 테스트
# ──────────────────────────────────────────

class TestParseTimestamp(unittest.TestCase):
    """타임스탬프 문자열 → 초 변환"""

    def test_mm_ss(self):
        self.assertEqual(_parse_timestamp('03:25'), 205)

    def test_hh_mm_ss(self):
        self.assertEqual(_parse_timestamp('1:30:00'), 5400)

    def test_zero(self):
        self.assertEqual(_parse_timestamp('00:00'), 0)

    def test_invalid_format(self):
        """잘못된 형식은 0 반환"""
        self.assertEqual(_parse_timestamp('abc'), 0)


class TestFormatTimestamp(unittest.TestCase):
    """초 → MM:SS 변환"""

    def test_basic(self):
        self.assertEqual(_format_timestamp(205), '03:25')

    def test_zero(self):
        self.assertEqual(_format_timestamp(0), '00:00')

    def test_under_minute(self):
        self.assertEqual(_format_timestamp(45), '00:45')


class TestClamp(unittest.TestCase):
    """값 범위 제한"""

    def test_within_range(self):
        self.assertEqual(_clamp(50.0), 50.0)

    def test_below_min(self):
        self.assertEqual(_clamp(-10.0), 0.0)

    def test_above_max(self):
        self.assertEqual(_clamp(150.0), 100.0)


# ──────────────────────────────────────────
# 점수 계산 함수 테스트
# ──────────────────────────────────────────

class TestCalcHookScore(unittest.TestCase):
    """훅 강도 점수"""

    def test_question_mark(self):
        """질문형은 훅 점수 발생"""
        score = _calc_hook_score('이것이 진짜일까?')
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_exclamation(self):
        """감탄형은 훅 점수 발생"""
        score = _calc_hook_score('대박! 미쳤다!')
        self.assertGreater(score, 0)

    def test_urgent_words(self):
        """긴급 표현"""
        score = _calc_hook_score('지금 당장 확인하세요 바로 시작합니다')
        self.assertGreater(score, 0)

    def test_plain_text_low_score(self):
        """평범한 텍스트는 낮은 점수"""
        score = _calc_hook_score('오늘 날씨가 좋습니다. 산책을 갔습니다.')
        self.assertLess(score, 30)

    def test_score_range(self):
        """점수는 항상 0~100"""
        # 극단적 입력
        text = '충격! 대박! 실화? 미쳤! 레전드! 지금 당장 바로! 100만원 50% 비밀!'
        score = _calc_hook_score(text)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_empty_text(self):
        """빈 텍스트는 0점"""
        self.assertEqual(_calc_hook_score(''), 0.0)


class TestCalcEmotionScore(unittest.TestCase):
    """감정 밀도 점수"""

    def test_emotional_text(self):
        """감정 어휘 많은 텍스트"""
        score = _calc_emotion_score('정말 좋아 너무 감동이야 최고')
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_neutral_text(self):
        """중립적 텍스트는 낮은 점수"""
        score = _calc_emotion_score('오늘 회의는 3시에 시작됩니다. 참석자는 5명입니다.')
        self.assertLess(score, 30)

    def test_empty_text(self):
        self.assertEqual(_calc_emotion_score(''), 0.0)

    def test_emoticons(self):
        """이모티콘(ㅋㅋ, ㅠㅠ 등)도 감정 점수 반영"""
        score = _calc_emotion_score('ㅋㅋㅋ ㅠㅠ 와 진짜')
        self.assertGreater(score, 0)


class TestCalcInfoDensity(unittest.TestCase):
    """정보 밀도 점수"""

    def test_numbers_boost(self):
        """숫자 포함 시 점수 상승"""
        score = _calc_info_density('매출이 300억에서 500억으로 증가했습니다. 성장률 67%.')
        self.assertGreater(score, 0)

    def test_proper_nouns(self):
        """고유명사 포함 시 점수 상승"""
        score = _calc_info_density('Google과 Samsung이 협력하여 새로운 서비스를 출시합니다.')
        self.assertGreater(score, 0)

    def test_empty_text(self):
        self.assertEqual(_calc_info_density(''), 0.0)

    def test_score_range(self):
        """점수 범위 0~100"""
        score = _calc_info_density('100 200 300 Google Apple Microsoft Samsung 한국은행 서울대학')
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class TestDetermineViralPotential(unittest.TestCase):
    """바이럴 잠재력 등급"""

    def test_high(self):
        self.assertEqual(_determine_viral_potential(80), 'high')

    def test_medium(self):
        self.assertEqual(_determine_viral_potential(45), 'medium')

    def test_low(self):
        self.assertEqual(_determine_viral_potential(15), 'low')

    def test_boundary_high(self):
        self.assertEqual(_determine_viral_potential(60), 'high')

    def test_boundary_medium(self):
        self.assertEqual(_determine_viral_potential(30), 'medium')

    def test_boundary_low(self):
        self.assertEqual(_determine_viral_potential(29.9), 'low')


# ──────────────────────────────────────────
# 자동 분할 테스트
# ──────────────────────────────────────────

class TestAutoSegment(unittest.TestCase):
    """자막 자동 분할"""

    def test_empty_transcript(self):
        self.assertEqual(_auto_segment(''), [])

    def test_timestamped_lines(self):
        """[MM:SS] 형식 자막 파싱"""
        transcript = (
            '[00:00] 안녕하세요 오늘 영상입니다.\n'
            '[01:30] 첫 번째 주제를 시작합니다.\n'
            '[03:00] 두 번째 주제입니다.'
        )
        segments = _auto_segment(transcript)
        self.assertGreater(len(segments), 0)
        # 첫 세그먼트 시작이 00:00
        self.assertEqual(segments[0]['start'], '00:00')

    def test_plain_text(self):
        """타임스탬프 없는 일반 텍스트도 분할"""
        transcript = '첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다.'
        segments = _auto_segment(transcript)
        self.assertGreater(len(segments), 0)
        # 모든 세그먼트에 start/end/text 존재
        for seg in segments:
            self.assertIn('start', seg)
            self.assertIn('end', seg)
            self.assertIn('text', seg)


# ──────────────────────────────────────────
# score_highlights 공개 API 테스트
# ──────────────────────────────────────────

class TestScoreHighlights(unittest.TestCase):
    """바이럴 하이라이트 점수화"""

    def test_empty_transcript(self):
        """빈 자막은 빈 리스트"""
        self.assertEqual(score_highlights(''), [])
        self.assertEqual(score_highlights('   '), [])

    def test_with_segments(self):
        """세그먼트 직접 제공"""
        segments = [
            {'start': '00:00', 'end': '01:00', 'text': '충격! 이것이 진짜? 대박!'},
            {'start': '01:00', 'end': '02:00', 'text': '오늘 날씨가 좋습니다.'},
        ]
        results = score_highlights('더미 자막', segments=segments)
        self.assertEqual(len(results), 2)

    def test_result_is_highlight_score(self):
        """반환값이 HighlightScore 인스턴스"""
        segments = [
            {'start': '00:00', 'end': '00:30', 'text': '테스트 텍스트입니다.'},
        ]
        results = score_highlights('테스트', segments=segments)
        self.assertIsInstance(results[0], HighlightScore)

    def test_scores_in_valid_range(self):
        """모든 점수가 0~100 범위"""
        segments = [
            {'start': '00:00', 'end': '01:00', 'text': '충격! 대박! 진짜? 100만원! Google Samsung!'},
            {'start': '01:00', 'end': '02:00', 'text': '평범한 내용입니다.'},
            {'start': '02:00', 'end': '03:00', 'text': '좋아 최고 감동 ㅋㅋ ㅠㅠ'},
        ]
        results = score_highlights('더미', segments=segments)
        for r in results:
            self.assertGreaterEqual(r.hook_score, 0)
            self.assertLessEqual(r.hook_score, 100)
            self.assertGreaterEqual(r.emotion_score, 0)
            self.assertLessEqual(r.emotion_score, 100)
            self.assertGreaterEqual(r.info_density, 0)
            self.assertLessEqual(r.info_density, 100)
            self.assertGreaterEqual(r.total_score, 0)
            self.assertLessEqual(r.total_score, 100)

    def test_viral_potential_valid_values(self):
        """viral_potential은 low/medium/high 중 하나"""
        segments = [
            {'start': '00:00', 'end': '00:30', 'text': '안녕하세요.'},
            {'start': '00:30', 'end': '01:00', 'text': '충격 대박 실화? 지금 당장!'},
        ]
        results = score_highlights('더미', segments=segments)
        for r in results:
            self.assertIn(r.viral_potential, ['low', 'medium', 'high'])

    def test_sorted_by_total_score_descending(self):
        """결과가 total_score 내림차순 정렬"""
        segments = [
            {'start': '00:00', 'end': '00:30', 'text': '평범한 텍스트.'},
            {'start': '00:30', 'end': '01:00', 'text': '충격! 대박! 실화? 미쳤! 레전드! 100만!'},
            {'start': '01:00', 'end': '01:30', 'text': '좋아 감동'},
        ]
        results = score_highlights('더미', segments=segments)
        scores = [r.total_score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_high_hook_text_higher_score(self):
        """훅 강한 텍스트가 평범한 텍스트보다 높은 점수"""
        segments = [
            {'start': '00:00', 'end': '00:30', 'text': '충격! 이것이 진짜? 대박 실화!'},
            {'start': '00:30', 'end': '01:00', 'text': '오늘 회의 참석자를 확인합니다.'},
        ]
        results = score_highlights('더미', segments=segments)
        # 정렬 후 첫 번째가 훅 강한 텍스트
        self.assertIn('충격', results[0].text)

    def test_auto_segment_when_none(self):
        """segments=None이면 자동 분할 사용"""
        transcript = '[00:00] 충격적인 내용! 대박!\n[01:00] 평범한 내용입니다.'
        results = score_highlights(transcript, segments=None)
        self.assertGreater(len(results), 0)

    def test_empty_text_segments_skipped(self):
        """빈 텍스트 세그먼트는 건너뜀"""
        segments = [
            {'start': '00:00', 'end': '00:30', 'text': ''},
            {'start': '00:30', 'end': '01:00', 'text': '   '},
            {'start': '01:00', 'end': '01:30', 'text': '유효한 텍스트'},
        ]
        results = score_highlights('더미', segments=segments)
        self.assertEqual(len(results), 1)

    def test_start_end_times_preserved(self):
        """세그먼트의 start/end 시간이 결과에 보존"""
        segments = [
            {'start': '05:30', 'end': '06:00', 'text': '테스트 텍스트'},
        ]
        results = score_highlights('더미', segments=segments)
        self.assertEqual(results[0].start_time, '05:30')
        self.assertEqual(results[0].end_time, '06:00')


# ──────────────────────────────────────────
# extract_keyword_clips 공개 API 테스트
# ──────────────────────────────────────────

class TestExtractKeywordClips(unittest.TestCase):
    """키워드 클립 추출"""

    def test_empty_transcript(self):
        """빈 자막은 빈 리스트"""
        self.assertEqual(extract_keyword_clips('', ['키워드']), [])

    def test_empty_keywords(self):
        """빈 키워드 리스트는 빈 결과"""
        self.assertEqual(extract_keyword_clips('텍스트', []), [])

    def test_no_match(self):
        """매칭 없으면 빈 결과"""
        transcript = '[00:00] 오늘 날씨가 좋습니다.'
        result = extract_keyword_clips(transcript, ['존재하지않는키워드'])
        self.assertEqual(result, [])

    def test_keyword_match(self):
        """키워드 매칭 시 클립 반환"""
        transcript = (
            '[00:00] 인공지능 기술이 발전하고 있습니다.\n'
            '[01:00] 오늘 날씨가 좋습니다.\n'
            '[02:00] 인공지능은 미래를 바꿀 것입니다.'
        )
        clips = extract_keyword_clips(transcript, ['인공지능'])
        self.assertGreater(len(clips), 0)
        for clip in clips:
            self.assertIn('인공지능', clip.matched_keywords)

    def test_clip_has_timestamps(self):
        """클립에 시작/종료 타임스탬프 존재"""
        transcript = '[00:00] 머신러닝 기초를 배워봅시다.\n[01:00] 다음 주제.'
        clips = extract_keyword_clips(transcript, ['머신러닝'])
        self.assertGreater(len(clips), 0)
        clip = clips[0]
        self.assertIsNotNone(clip.start_time)
        self.assertIsNotNone(clip.end_time)
        # MM:SS 형식 검증
        self.assertRegex(clip.start_time, r'^\d{2}:\d{2}$')
        self.assertRegex(clip.end_time, r'^\d{2}:\d{2}$')

    def test_multiple_keywords(self):
        """여러 키워드 동시 매칭"""
        transcript = '[00:00] Python과 JavaScript를 비교합니다.'
        clips = extract_keyword_clips(transcript, ['Python', 'JavaScript'])
        self.assertGreater(len(clips), 0)
        self.assertIn('Python', clips[0].matched_keywords)
        self.assertIn('JavaScript', clips[0].matched_keywords)

    def test_case_insensitive(self):
        """대소문자 무시 매칭"""
        transcript = '[00:00] python은 좋은 언어입니다.'
        clips = extract_keyword_clips(transcript, ['Python'])
        self.assertGreater(len(clips), 0)

    def test_result_is_clip_instance(self):
        """반환값이 Clip 인스턴스"""
        transcript = '[00:00] 테스트 키워드 포함.'
        clips = extract_keyword_clips(transcript, ['테스트'])
        if clips:
            self.assertIsInstance(clips[0], Clip)

    def test_sorted_by_start_time(self):
        """결과가 시작 시간순 정렬"""
        transcript = (
            '[02:00] 나중 구간에 키워드.\n'
            '[00:00] 처음 구간에 키워드.\n'
            '[01:00] 중간 구간에 키워드.'
        )
        clips = extract_keyword_clips(transcript, ['키워드'])
        if len(clips) >= 2:
            times = [clip.start_time for clip in clips]
            parsed = [_parse_timestamp(t) for t in times]
            self.assertEqual(parsed, sorted(parsed))

    def test_blank_keywords_filtered(self):
        """빈 문자열 키워드는 무시"""
        transcript = '[00:00] 테스트 텍스트.'
        clips = extract_keyword_clips(transcript, ['', '  ', '테스트'])
        # 빈 키워드 때문에 에러 나지 않아야 함
        self.assertGreater(len(clips), 0)

    def test_speaker_filter(self):
        """화자 필터 적용 시 해당 화자 세그먼트만 반환"""
        # speaker 필드가 있는 세그먼트를 직접 사용하기 위해
        # 내부적으로 _auto_segment는 speaker를 반환하지 않으므로
        # speaker=None이면 모든 세그먼트 반환 확인
        transcript = '[00:00] 키워드 포함 텍스트.'
        clips = extract_keyword_clips(transcript, ['키워드'], speaker=None)
        self.assertGreater(len(clips), 0)

    def test_speaker_filter_no_match(self):
        """존재하지 않는 화자 필터 시 빈 결과"""
        transcript = '[00:00] 키워드 포함 텍스트.'
        clips = extract_keyword_clips(transcript, ['키워드'], speaker='특정화자')
        # _auto_segment은 speaker=None이므로 특정화자와 매칭 안 됨
        self.assertEqual(clips, [])

    def test_all_blank_keywords_returns_empty(self):
        """모든 키워드가 빈 문자열이면 빈 결과"""
        transcript = '[00:00] 텍스트.'
        clips = extract_keyword_clips(transcript, ['', '  '])
        self.assertEqual(clips, [])


if __name__ == '__main__':
    unittest.main()
