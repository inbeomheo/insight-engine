"""
Phase 2 Group A 단위 테스트

F2-01 TTS 장문 분할, F2-03 슬라이드, F2-10 워드클라우드,
F2-17 RSS, F2-19 SRT 내보내기
"""
import unittest
from unittest.mock import patch, MagicMock

from services.tts_service import _split_text, preprocess_for_tts
from services.slide_service import convert_to_slides
from services.wordcloud_service import generate_wordcloud, _count_words


class TestTTSSplitText(unittest.TestCase):
    """TTS 장문 분할 테스트"""

    def test_short_text_no_split(self):
        """짧은 텍스트는 분할하지 않음"""
        result = _split_text('짧은 텍스트입니다.', 100)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], '짧은 텍스트입니다.')

    def test_split_at_sentence_boundary(self):
        """문장 경계에서 분할"""
        text = '첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다.'
        result = _split_text(text, 25)
        self.assertGreater(len(result), 1)
        # 모든 청크가 비어있지 않아야 함
        for chunk in result:
            self.assertTrue(chunk.strip())

    def test_empty_chunks_filtered(self):
        """빈 청크는 필터링됨"""
        result = _split_text('Hello. World.', 10)
        for chunk in result:
            self.assertTrue(chunk.strip())

    def test_preprocess_removes_markdown(self):
        """마크다운 서식이 제거됨"""
        md = '# 제목\n\n**볼드** 텍스트\n\n```python\ncode\n```'
        result = preprocess_for_tts(md)
        self.assertNotIn('#', result)
        self.assertNotIn('**', result)
        self.assertNotIn('```', result)


class TestSlideService(unittest.TestCase):
    """슬라이드 변환 테스트"""

    def test_basic_conversion(self):
        """기본 마크다운 → 슬라이드 변환"""
        md = '## 슬라이드 1\n\n내용 1\n\n## 슬라이드 2\n\n내용 2'
        html = convert_to_slides(md)
        self.assertIn('<section>', html)
        self.assertIn('reveal.js', html)
        self.assertIn('슬라이드 1', html)
        self.assertIn('슬라이드 2', html)

    def test_empty_content_raises(self):
        """빈 콘텐츠는 ValueError"""
        with self.assertRaises(ValueError):
            convert_to_slides('')

    def test_code_block_preserved(self):
        """코드 블록이 보존됨"""
        md = '## 코드\n\n```python\nprint("hello")\n```'
        html = convert_to_slides(md)
        self.assertIn('<pre>', html)
        self.assertIn('print', html)

    def test_theme_applied(self):
        """테마가 적용됨"""
        html = convert_to_slides('## Test', theme='white')
        self.assertIn('theme/white.css', html)

    def test_bullet_list(self):
        """불릿 목록이 HTML <li>로 변환됨"""
        md = '## 목록\n\n- 항목 1\n- 항목 2'
        html = convert_to_slides(md)
        self.assertIn('<li>', html)


class TestWordcloudService(unittest.TestCase):
    """워드클라우드 테스트"""

    def test_basic_generation(self):
        """기본 워드클라우드 생성"""
        text = '파이썬 프로그래밍 파이썬 개발 파이썬 자바스크립트 개발 프로그래밍'
        svg = generate_wordcloud(text)
        self.assertIn('<svg', svg)
        self.assertIn('파이썬', svg)

    def test_empty_text_raises(self):
        """빈 텍스트는 ValueError"""
        with self.assertRaises(ValueError):
            generate_wordcloud('')

    def test_stopwords_filtered(self):
        """불용어가 필터링됨"""
        counts = _count_words('the the the python python javascript', 10)
        words = [w for w, _ in counts]
        self.assertNotIn('the', words)
        self.assertIn('python', words)

    def test_max_words_limit(self):
        """최대 단어 수 제한"""
        text = ' '.join(f'word{i} ' * (10 - i) for i in range(20))
        counts = _count_words(text, 5)
        self.assertLessEqual(len(counts), 5)


class TestSRTConversion(unittest.TestCase):
    """SRT 변환 테스트"""

    def test_seconds_to_srt_time(self):
        """초 → SRT 타임코드 변환"""
        from routes.export_routes import _seconds_to_srt_time
        self.assertEqual(_seconds_to_srt_time(0), '00:00:00,000')
        self.assertEqual(_seconds_to_srt_time(61.5), '00:01:01,500')
        self.assertEqual(_seconds_to_srt_time(3661.123), '01:01:01,123')

    def test_negative_seconds(self):
        """음수는 0으로 처리"""
        from routes.export_routes import _seconds_to_srt_time
        self.assertEqual(_seconds_to_srt_time(-5), '00:00:00,000')


class TestRSSFeed(unittest.TestCase):
    """RSS 피드 테스트"""

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_rss_without_supabase(self, _mock):
        """Supabase 없이도 RSS 피드 생성 가능"""
        from app import create_app
        app = create_app()
        with app.test_client() as client:
            resp = client.get('/feed.xml')
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b'<rss', resp.data)
            self.assertIn(b'Insight Engine', resp.data)


if __name__ == '__main__':
    unittest.main()
