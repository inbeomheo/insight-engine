"""highlight_graph_service 단위 테스트"""
import unittest

from services.highlight_graph_service import (
    TimelinePoint,
    InterestTimeline,
    PreviewClip,
    build_interest_timeline,
    generate_preview,
    _time_to_seconds,
    _seconds_to_time,
    _parse_segments,
    _calculate_interest,
    _find_peak_moments,
    _generate_label,
)


class TestTimeToSeconds(unittest.TestCase):
    """_time_to_seconds 테스트"""

    def test_mm_ss(self):
        self.assertEqual(_time_to_seconds('3:25'), 205)

    def test_hh_mm_ss(self):
        self.assertEqual(_time_to_seconds('1:02:30'), 3750)

    def test_zero(self):
        self.assertEqual(_time_to_seconds('0:00'), 0)


class TestSecondsToTime(unittest.TestCase):
    """_seconds_to_time 테스트"""

    def test_under_hour(self):
        self.assertEqual(_seconds_to_time(205), '3:25')

    def test_over_hour(self):
        self.assertEqual(_seconds_to_time(3750), '1:02:30')

    def test_zero(self):
        self.assertEqual(_seconds_to_time(0), '0:00')


class TestParseSegments(unittest.TestCase):
    """_parse_segments 테스트"""

    def test_with_timestamps(self):
        """타임스탬프 포함 자막 파싱"""
        transcript = '[0:00] 시작 [1:30] 중간 [3:00] 끝'
        result = _parse_segments(transcript)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['time'], '0:00')
        self.assertEqual(result[0]['text'], '시작')
        self.assertEqual(result[1]['time_seconds'], 90)

    def test_without_timestamps(self):
        """타임스탬프 없으면 30초 간격 가상 타임스탬프"""
        transcript = '첫째 줄\n둘째 줄\n셋째 줄'
        result = _parse_segments(transcript)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['time_seconds'], 0)
        self.assertEqual(result[1]['time_seconds'], 30)
        self.assertEqual(result[2]['time_seconds'], 60)

    def test_empty(self):
        """빈 자막"""
        self.assertEqual(_parse_segments(''), [])

    def test_whitespace_only(self):
        """공백만 있는 자막"""
        self.assertEqual(_parse_segments('   \n  '), [])


class TestCalculateInterest(unittest.TestCase):
    """_calculate_interest 테스트"""

    def test_empty_text(self):
        """빈 텍스트 → 0.0"""
        self.assertEqual(_calculate_interest(''), 0.0)

    def test_plain_text(self):
        """일반 텍스트 → 기본 관심도 (0.2 근처)"""
        score = _calculate_interest('일반적인 내용입니다')
        self.assertGreaterEqual(score, 0.2)
        self.assertLess(score, 0.5)

    def test_high_interest_keywords(self):
        """핵심 키워드 포함 시 관심도 상승"""
        score = _calculate_interest('이것이 핵심 비밀입니다! 중요한 결론!')
        self.assertGreater(score, 0.5)

    def test_exclamation_pattern(self):
        """느낌표 다수 → 패턴 매칭 보너스"""
        plain = _calculate_interest('내용입니다')
        excited = _calculate_interest('내용입니다!!')
        self.assertGreater(excited, plain)

    def test_question_bonus(self):
        """질문 포함 보너스"""
        statement = _calculate_interest('이것은 설명입니다')
        question = _calculate_interest('이것은 무엇일까요?')
        self.assertGreater(question, statement)

    def test_max_is_one(self):
        """관심도는 최대 1.0"""
        score = _calculate_interest(
            '중요!! 핵심 비밀 꿀팁 결론 요약 대박 최고 역대급 레전드 충격!! '
            '놀랍!! 드디어 공개 발표!! 100만!? WHY?'
        )
        self.assertLessEqual(score, 1.0)

    def test_longer_text_bonus(self):
        """긴 텍스트는 약간의 보너스"""
        short = _calculate_interest('짧은')
        long_text = _calculate_interest('이것은 매우 긴 텍스트입니다. ' * 20)
        self.assertGreaterEqual(long_text, short)


class TestGenerateLabel(unittest.TestCase):
    """_generate_label 테스트"""

    def test_with_keywords(self):
        """키워드가 있으면 라벨 생성"""
        label = _generate_label('이것이 핵심 비밀입니다')
        self.assertIsNotNone(label)
        self.assertIn('핵심', label)

    def test_no_keywords(self):
        """키워드 없으면 None"""
        label = _generate_label('일반적인 내용입니다')
        self.assertIsNone(label)

    def test_max_two_keywords(self):
        """라벨에 최대 2개 키워드"""
        label = _generate_label('핵심 비밀 결론 요약')
        if label:
            parts = label.split(' / ')
            self.assertLessEqual(len(parts), 2)


class TestFindPeakMoments(unittest.TestCase):
    """_find_peak_moments 테스트"""

    def test_single_peak(self):
        """단일 피크 구간 추출"""
        points = [
            TimelinePoint(time='0:00', interest_level=0.3),
            TimelinePoint(time='0:30', interest_level=0.7, label='핵심'),
            TimelinePoint(time='1:00', interest_level=0.8, label='비밀'),
            TimelinePoint(time='1:30', interest_level=0.3),
        ]
        peaks = _find_peak_moments(points, threshold=0.6)
        self.assertEqual(len(peaks), 1)
        self.assertEqual(peaks[0]['start'], '0:30')
        self.assertEqual(peaks[0]['end'], '1:00')
        self.assertAlmostEqual(peaks[0]['peak_interest'], 0.8)

    def test_multiple_peaks(self):
        """다중 피크 구간"""
        points = [
            TimelinePoint(time='0:00', interest_level=0.8),
            TimelinePoint(time='0:30', interest_level=0.3),
            TimelinePoint(time='1:00', interest_level=0.9),
        ]
        peaks = _find_peak_moments(points, threshold=0.6)
        self.assertEqual(len(peaks), 2)

    def test_no_peaks(self):
        """피크 없음"""
        points = [
            TimelinePoint(time='0:00', interest_level=0.2),
            TimelinePoint(time='0:30', interest_level=0.3),
        ]
        peaks = _find_peak_moments(points, threshold=0.6)
        self.assertEqual(peaks, [])

    def test_empty_points(self):
        """빈 포인트 목록"""
        self.assertEqual(_find_peak_moments([], threshold=0.6), [])

    def test_peak_at_end(self):
        """마지막 포인트가 피크인 경우"""
        points = [
            TimelinePoint(time='0:00', interest_level=0.3),
            TimelinePoint(time='0:30', interest_level=0.8),
        ]
        peaks = _find_peak_moments(points, threshold=0.6)
        self.assertEqual(len(peaks), 1)
        self.assertEqual(peaks[0]['start'], '0:30')


class TestBuildInterestTimeline(unittest.TestCase):
    """build_interest_timeline 통합 테스트"""

    def test_basic_timeline(self):
        """기본 타임라인 생성"""
        transcript = '[0:00] 안녕하세요 [1:00] 핵심 비밀 공개 [2:00] 마무리'
        result = build_interest_timeline(transcript, video_id='test123')

        self.assertIsInstance(result, InterestTimeline)
        self.assertEqual(result.video_id, 'test123')
        self.assertEqual(len(result.points), 3)
        self.assertGreater(result.average_interest, 0.0)

    def test_empty_transcript(self):
        """빈 자막 → 빈 타임라인"""
        result = build_interest_timeline('', video_id='empty')
        self.assertEqual(result.video_id, 'empty')
        self.assertEqual(result.points, [])
        self.assertEqual(result.average_interest, 0.0)

    def test_whitespace_transcript(self):
        """공백만 있는 자막"""
        result = build_interest_timeline('   \n  ')
        self.assertEqual(result.points, [])

    def test_default_video_id(self):
        """video_id 미지정 시 빈 문자열"""
        result = build_interest_timeline('[0:00] 테스트')
        self.assertEqual(result.video_id, '')

    def test_points_have_valid_interest(self):
        """모든 포인트의 관심도가 0.0~1.0 범위"""
        transcript = '[0:00] 시작 [0:30] 중요한 핵심!! [1:00] 끝'
        result = build_interest_timeline(transcript)
        for point in result.points:
            self.assertGreaterEqual(point.interest_level, 0.0)
            self.assertLessEqual(point.interest_level, 1.0)

    def test_peak_moments_populated(self):
        """고관심도 구간에 peak_moments가 생성됨"""
        # 핵심 키워드를 다수 포함하여 확실히 임계값 초과
        transcript = (
            '[0:00] 일반적인 내용 '
            '[0:30] 중요 핵심 비밀 결론 요약!! '
            '[1:00] 평범한 마무리'
        )
        result = build_interest_timeline(transcript)
        # 고관심도 키워드가 많은 0:30 구간이 피크로 잡혀야 함
        high_points = [p for p in result.points if p.interest_level >= 0.6]
        if high_points:
            self.assertGreater(len(result.peak_moments), 0)

    def test_without_timestamps(self):
        """타임스탬프 없는 자막도 처리"""
        transcript = '첫 번째 내용\n두 번째 내용\n세 번째 내용'
        result = build_interest_timeline(transcript)
        self.assertEqual(len(result.points), 3)
        self.assertEqual(result.points[0].time, '0:00')
        self.assertEqual(result.points[1].time, '0:30')


class TestGeneratePreview(unittest.TestCase):
    """generate_preview 테스트"""

    def test_basic_preview(self):
        """기본 프리뷰 클립 생성"""
        timeline = InterestTimeline(
            video_id='test',
            points=[
                TimelinePoint(time='0:00', interest_level=0.3),
                TimelinePoint(time='1:00', interest_level=0.9, label='핵심'),
                TimelinePoint(time='2:00', interest_level=0.5),
                TimelinePoint(time='3:00', interest_level=0.8, label='비밀'),
            ],
            peak_moments=[],
            average_interest=0.6,
        )
        clips = generate_preview(timeline, top_n=2)
        self.assertEqual(len(clips), 2)
        # 관심도 높은 순
        self.assertGreaterEqual(clips[0].interest_level, clips[1].interest_level)

    def test_preview_clip_fields(self):
        """PreviewClip 필드 검증"""
        timeline = InterestTimeline(
            video_id='test',
            points=[
                TimelinePoint(time='5:00', interest_level=0.9, label='핵심 포인트'),
            ],
        )
        clips = generate_preview(timeline, top_n=1)
        self.assertEqual(len(clips), 1)
        self.assertIsInstance(clips[0], PreviewClip)
        self.assertEqual(clips[0].start_time, '5:00')
        self.assertEqual(clips[0].end_time, '5:30')
        self.assertEqual(clips[0].interest_level, 0.9)
        self.assertEqual(clips[0].description, '핵심 포인트')

    def test_empty_timeline(self):
        """빈 타임라인 → 빈 클립"""
        timeline = InterestTimeline(video_id='empty')
        clips = generate_preview(timeline)
        self.assertEqual(clips, [])

    def test_overlap_prevention(self):
        """30초 이내 겹침 방지"""
        timeline = InterestTimeline(
            video_id='test',
            points=[
                TimelinePoint(time='1:00', interest_level=0.9),
                TimelinePoint(time='1:10', interest_level=0.85),  # 겹침
                TimelinePoint(time='3:00', interest_level=0.8),
            ],
        )
        clips = generate_preview(timeline, top_n=3)
        # 1:00과 1:10이 겹치므로 최대 2개
        self.assertLessEqual(len(clips), 2)
        times = [_time_to_seconds(c.start_time) for c in clips]
        # 모든 쌍이 30초 이상 차이
        for i in range(len(times)):
            for j in range(i + 1, len(times)):
                self.assertGreaterEqual(abs(times[i] - times[j]), 30)

    def test_top_n_limit(self):
        """top_n 개수 제한"""
        points = [
            TimelinePoint(time=_seconds_to_time(i * 60), interest_level=0.5 + i * 0.05)
            for i in range(10)
        ]
        timeline = InterestTimeline(video_id='test', points=points)
        clips = generate_preview(timeline, top_n=3)
        self.assertLessEqual(len(clips), 3)

    def test_description_fallback(self):
        """라벨 없으면 기본 설명 생성"""
        timeline = InterestTimeline(
            video_id='test',
            points=[
                TimelinePoint(time='0:00', interest_level=0.7, label=None),
            ],
        )
        clips = generate_preview(timeline, top_n=1)
        self.assertIn('관심도', clips[0].description)
        self.assertIn('70%', clips[0].description)


if __name__ == '__main__':
    unittest.main()
