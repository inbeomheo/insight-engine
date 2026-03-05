"""
이미지 생성 서비스 단위 테스트
- thumbnail_service
- infographic_service
- card_news_service
- summary_card_service
- code_image_service
"""
import base64
import unittest
from unittest.mock import patch, MagicMock

from services.infographic_service import generate_infographic, _extract_key_points, _extract_stats
from services.card_news_service import generate_card_news, _split_content_to_points
from services.summary_card_service import generate_summary_card
from services.code_image_service import generate_code_image


SAMPLE_CONTENT = """
# 인공지능의 미래

## 1. 딥러닝 혁명
- 자연어 처리 분야에서 큰 발전
- 이미지 인식 정확도 98% 달성
- 자율주행 기술의 핵심

## 2. 생성형 AI
- GPT 시리즈의 진화
- 이미지 생성 AI 등장
- 코드 자동 생성

## 3. 산업 적용
1. 의료 진단 보조
2. 금융 리스크 분석
3. 제조업 품질 관리
"""


class TestInfographicService(unittest.TestCase):
    """인포그래픽 서비스 테스트"""

    def test_generate_infographic_returns_html(self):
        """HTML 인포그래픽이 생성되는지 확인"""
        result = generate_infographic(SAMPLE_CONTENT, '인공지능의 미래')
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('인공지능의 미래', result)

    def test_generate_infographic_empty_content(self):
        """빈 콘텐츠 시 안내 메시지"""
        result = generate_infographic('', '제목')
        self.assertIn('콘텐츠가 없습니다', result)

    def test_extract_key_points(self):
        """핵심 포인트 추출"""
        points = _extract_key_points(SAMPLE_CONTENT)
        self.assertGreater(len(points), 0)
        self.assertLessEqual(len(points), 8)

    def test_extract_stats(self):
        """통계 데이터 추출"""
        stats = _extract_stats('정확도 98%를 달성했고, 1000개의 샘플을 분석')
        self.assertGreater(len(stats), 0)

    def test_extract_stats_empty(self):
        """숫자 없는 텍스트"""
        stats = _extract_stats('숫자가 없는 텍스트')
        self.assertEqual(len(stats), 0)


class TestCardNewsService(unittest.TestCase):
    """카드뉴스 서비스 테스트"""

    def test_generate_card_news_returns_svgs(self):
        """SVG 카드 리스트가 생성되는지 확인"""
        cards = generate_card_news(SAMPLE_CONTENT, '인공지능 카드뉴스')
        self.assertGreater(len(cards), 0)
        for card in cards:
            self.assertIn('<svg', card)
            self.assertIn('</svg>', card)

    def test_generate_card_news_empty(self):
        """빈 콘텐츠 시 빈 리스트"""
        cards = generate_card_news('')
        self.assertEqual(cards, [])

    def test_split_content_to_points(self):
        """포인트 분할"""
        points = _split_content_to_points(SAMPLE_CONTENT)
        self.assertGreater(len(points), 0)
        self.assertLessEqual(len(points), 10)

    def test_title_card_included(self):
        """첫 카드가 제목 카드인지 확인"""
        cards = generate_card_news(SAMPLE_CONTENT, '제목 테스트')
        self.assertGreater(len(cards), 0)
        # 첫 카드에 제목 텍스트 또는 카드뉴스 문구 포함
        self.assertIn('카드뉴스', cards[0])


class TestSummaryCardService(unittest.TestCase):
    """요약 카드 서비스 테스트"""

    def test_generate_summary_card_returns_svg(self):
        """SVG 요약 카드 생성"""
        svg = generate_summary_card('테스트 제목', ['포인트 1', '포인트 2', '포인트 3'])
        self.assertIn('<svg', svg)
        self.assertIn('테스트 제목', svg)
        self.assertIn('포인트 1', svg)

    def test_max_five_points(self):
        """최대 5개 포인트 제한"""
        points = [f'포인트 {i}' for i in range(10)]
        svg = generate_summary_card('제목', points)
        # 6번째 포인트는 포함되지 않아야 함
        self.assertNotIn('포인트 5', svg)  # 0-indexed, 5번째 = 6번째 항목

    def test_empty_points(self):
        """빈 포인트 리스트"""
        svg = generate_summary_card('제목', [])
        self.assertIn('<svg', svg)

    def test_long_title_wraps(self):
        """긴 제목 줄바꿈 처리"""
        svg = generate_summary_card('이것은 매우 매우 매우 매우 긴 제목입니다', ['포인트'])
        self.assertIn('tspan', svg)


class TestCodeImageService(unittest.TestCase):
    """코드 이미지 서비스 테스트"""

    def test_generate_code_image_html(self):
        """HTML 코드 이미지 생성"""
        code = 'def hello():\n    print("Hello, World!")'
        result = generate_code_image(code, 'python', 'hello.py')
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('hello.py', result)

    def test_empty_code(self):
        """빈 코드"""
        result = generate_code_image('', 'python')
        self.assertIn('코드가 없습니다', result)

    def test_line_numbers(self):
        """줄 번호가 포함되는지 확인"""
        code = 'line1\nline2\nline3'
        result = generate_code_image(code, 'python')
        self.assertIn('>1<', result)
        self.assertIn('>2<', result)
        self.assertIn('>3<', result)

    def test_javascript_highlighting(self):
        """JavaScript 키워드 하이라이팅"""
        code = 'const x = 42;'
        result = generate_code_image(code, 'javascript')
        self.assertIn('font-weight:700', result)  # 키워드 볼드

    def test_carbon_style_header(self):
        """carbon.sh 스타일 헤더 (3개 점)"""
        code = 'x = 1'
        result = generate_code_image(code, 'python')
        self.assertIn('border-radius:50%', result)  # 둥근 점


class TestThumbnailService(unittest.TestCase):
    """썸네일 서비스 테스트"""

    @patch('services.thumbnail_service.IMAGE_GEN_API_KEY', '')
    def test_no_api_key(self):
        """API 키 없을 때 에러"""
        from services.thumbnail_service import generate_thumbnail
        result = generate_thumbnail('테스트')
        self.assertFalse(result['success'])
        self.assertIn('API 키', result['error'])

    @patch('services.thumbnail_service.IMAGE_GEN_API_KEY', 'test-key')
    @patch('services.thumbnail_service.generate_image')
    def test_successful_generation(self, mock_gen):
        """정상 생성"""
        mock_gen.return_value = b'\x89PNG_fake_image_data'
        from services.thumbnail_service import generate_thumbnail
        result = generate_thumbnail('테스트 제목', ['키워드1'])
        self.assertTrue(result['success'])
        self.assertIn('image_base64', result)

    def test_empty_title(self):
        """빈 제목"""
        from services.thumbnail_service import generate_thumbnail
        result = generate_thumbnail('')
        self.assertFalse(result['success'])

    def test_build_image_prompt(self):
        """프롬프트 생성"""
        from services.thumbnail_service import _build_image_prompt
        prompt = _build_image_prompt('AI 튜토리얼', ['파이썬', '머신러닝'])
        self.assertIn('AI', prompt)
        self.assertIn('thumbnail', prompt.lower())


class TestImageGenService(unittest.TestCase):
    """이미지 생성 서비스 테스트"""

    def test_invalid_size(self):
        """잘못된 이미지 크기"""
        from services.image_gen_service import generate_image
        with self.assertRaises(ValueError):
            generate_image('test', size='999x999')

    @patch('services.image_gen_service.IMAGE_GEN_API_KEY', '')
    def test_no_api_key_raises(self):
        """API 키 없을 때 ValueError"""
        from services.image_gen_service import generate_image
        with self.assertRaises(ValueError):
            generate_image('test')

    def test_invalid_provider(self):
        """지원하지 않는 프로바이더"""
        import services.image_gen_service as svc
        original = svc.IMAGE_GEN_PROVIDER
        svc.IMAGE_GEN_API_KEY = 'fake-key'
        svc.IMAGE_GEN_PROVIDER = 'invalid_provider'
        try:
            with self.assertRaises(ValueError):
                svc.generate_image('test')
        finally:
            svc.IMAGE_GEN_PROVIDER = original


if __name__ == '__main__':
    unittest.main()
