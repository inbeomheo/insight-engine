"""commentary_podcast_service 단위 테스트"""
import unittest

from services.commentary_podcast_service import (
    generate_commentary,
    PodcastScript,
    PodcastSegment,
    SEGMENT_TYPES,
    _estimate_duration,
    _extract_title,
    _split_into_paragraphs,
)


class TestGenerateCommentary(unittest.TestCase):
    """generate_commentary 함수 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠 — 빈 대본"""
        result = generate_commentary('')
        self.assertEqual(result.title, '빈 에피소드')
        self.assertEqual(result.segments, [])
        self.assertEqual(result.total_duration_minutes, 0.0)

    def test_whitespace_only(self):
        """공백만 있는 콘텐츠"""
        result = generate_commentary('   \n\n  ')
        self.assertEqual(result.segments, [])

    def test_basic_content(self):
        """기본 콘텐츠 — 인트로/본론/코멘터리/아웃트로 생성"""
        content = '# 테스트 제목\n\n첫 번째 문단입니다.\n\n두 번째 문단입니다.'
        result = generate_commentary(content, host_name='MC김')
        self.assertIsInstance(result, PodcastScript)
        self.assertEqual(result.host, 'MC김')
        self.assertGreater(len(result.segments), 0)

    def test_has_intro_and_outro(self):
        """인트로와 아웃트로 세그먼트 존재"""
        content = '주제 설명입니다.'
        result = generate_commentary(content)
        types = [s.segment_type for s in result.segments]
        self.assertIn('intro', types)
        self.assertIn('outro', types)

    def test_has_commentary(self):
        """코멘터리 세그먼트 존재"""
        content = '내용 1.\n\n내용 2.'
        result = generate_commentary(content)
        types = [s.segment_type for s in result.segments]
        self.assertIn('commentary', types)

    def test_has_main_segments(self):
        """본론 세그먼트 존재"""
        content = '첫 번째 문단.\n\n두 번째 문단.'
        result = generate_commentary(content)
        main_segments = [s for s in result.segments if s.segment_type == 'main']
        self.assertGreater(len(main_segments), 0)

    def test_total_duration_matches_sum(self):
        """전체 시간 = 세그먼트 시간 합산"""
        content = '문단 하나.\n\n문단 둘.'
        result = generate_commentary(content)
        expected = round(sum(s.duration_minutes for s in result.segments), 2)
        self.assertEqual(result.total_duration_minutes, expected)

    def test_default_host_name(self):
        """기본 호스트 이름 'Host'"""
        result = generate_commentary('내용')
        self.assertEqual(result.host, 'Host')

    def test_custom_host_name(self):
        """커스텀 호스트 이름"""
        result = generate_commentary('내용', host_name='진행자')
        self.assertEqual(result.host, '진행자')
        # 인트로에 호스트 이름 포함
        intro = [s for s in result.segments if s.segment_type == 'intro']
        self.assertTrue(any('진행자' in s.text for s in intro))

    def test_title_extraction(self):
        """제목 추출 — 마크다운 헤딩"""
        content = '## 오늘의 주제\n\n내용입니다.'
        result = generate_commentary(content)
        self.assertEqual(result.title, '오늘의 주제')

    def test_segment_types_valid(self):
        """모든 세그먼트 타입이 유효"""
        content = '내용.\n\n추가 내용.'
        result = generate_commentary(content)
        for seg in result.segments:
            self.assertIn(seg.segment_type, SEGMENT_TYPES)

    def test_segment_duration_positive(self):
        """모든 세그먼트 시간이 양수"""
        content = '긴 내용입니다 ' * 20
        result = generate_commentary(content)
        for seg in result.segments:
            self.assertGreater(seg.duration_minutes, 0.0)


class TestHelperFunctions(unittest.TestCase):
    """헬퍼 함수 테스트"""

    def test_estimate_duration_empty(self):
        """빈 텍스트 → 0분"""
        self.assertEqual(_estimate_duration(''), 0.0)

    def test_estimate_duration_150_words(self):
        """150단어 → 약 1분"""
        text = 'word ' * 150
        dur = _estimate_duration(text)
        self.assertAlmostEqual(dur, 1.0, places=1)

    def test_extract_title_plain(self):
        """일반 텍스트 첫 줄 = 제목"""
        self.assertEqual(_extract_title('제목입니다\n본문'), '제목입니다')

    def test_extract_title_markdown(self):
        """마크다운 헤딩 제거"""
        self.assertEqual(_extract_title('# 마크다운 제목'), '마크다운 제목')

    def test_extract_title_empty(self):
        """빈 텍스트 → 기본 제목"""
        self.assertEqual(_extract_title(''), '팟캐스트 에피소드')

    def test_split_into_paragraphs(self):
        """문단 분리"""
        content = '첫째.\n\n둘째.\n\n셋째.'
        paras = _split_into_paragraphs(content)
        self.assertEqual(len(paras), 3)

    def test_split_removes_empty(self):
        """빈 문단 제거"""
        content = 'A\n\n\n\nB'
        paras = _split_into_paragraphs(content)
        self.assertEqual(len(paras), 2)


if __name__ == '__main__':
    unittest.main()
