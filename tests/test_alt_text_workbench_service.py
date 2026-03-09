"""ALT 텍스트 워크벤치 서비스 테스트."""
import unittest

from services.alt_text_workbench_service import (
    AltText,
    generate_alt_texts,
    validate_alt_text,
    _extract_keywords_from_filename,
    _find_relevant_context,
    _build_alt_text,
    _calculate_quality_score,
)


class TestExtractKeywordsFromFilename(unittest.TestCase):
    """파일명 키워드 추출 테스트."""

    def test_basic_filename(self):
        """기본 파일명에서 키워드 추출."""
        keywords = _extract_keywords_from_filename('sales-chart.png')
        self.assertIn('sales', keywords)
        self.assertIn('chart', keywords)

    def test_underscore_separator(self):
        """언더스코어 구분자 처리."""
        keywords = _extract_keywords_from_filename('revenue_graph_2024.jpg')
        self.assertIn('revenue', keywords)
        self.assertIn('graph', keywords)
        # 순수 숫자는 제거
        self.assertNotIn('2024', keywords)

    def test_noise_removal(self):
        """노이즈 단어(img, photo 등) 제거."""
        keywords = _extract_keywords_from_filename('img_logo_design.png')
        self.assertNotIn('img', [k.lower() for k in keywords])
        self.assertIn('logo', keywords)
        self.assertIn('design', keywords)

    def test_extension_removal(self):
        """파일 확장자 제거."""
        keywords = _extract_keywords_from_filename('banner.webp')
        self.assertIn('banner', keywords)
        self.assertNotIn('webp', keywords)

    def test_empty_filename(self):
        """빈 파일명 처리."""
        keywords = _extract_keywords_from_filename('')
        self.assertEqual(keywords, [])


class TestFindRelevantContext(unittest.TestCase):
    """페이지 문맥 관련 문장 탐색 테스트."""

    def test_finds_matching_sentence(self):
        """키워드와 관련된 문장 탐색."""
        context = '이번 분기 매출은 20% 성장했습니다. chart가 보여주는 추세는 긍정적입니다.'
        result = _find_relevant_context(context, ['chart'])
        self.assertIsNotNone(result)
        self.assertIn('chart', result)

    def test_no_match(self):
        """관련 없는 문맥에서는 None 반환."""
        context = '오늘 날씨가 좋습니다.'
        result = _find_relevant_context(context, ['architecture'])
        self.assertIsNone(result)

    def test_empty_context(self):
        """빈 문맥에서 None 반환."""
        result = _find_relevant_context('', ['chart'])
        self.assertIsNone(result)

    def test_empty_keywords(self):
        """빈 키워드에서 None 반환."""
        result = _find_relevant_context('테스트 문장입니다.', [])
        self.assertIsNone(result)


class TestBuildAltText(unittest.TestCase):
    """ALT 텍스트 생성 테스트."""

    def test_caption_priority(self):
        """캡션이 있으면 우선 사용."""
        image = {'id': 'img1', 'filename': 'chart.png', 'caption': '2024년 매출 추이 그래프'}
        alt = _build_alt_text(image)
        self.assertEqual(alt, '2024년 매출 추이 그래프')

    def test_filename_fallback(self):
        """캡션이 없으면 파일명에서 키워드 추출."""
        image = {'id': 'img2', 'filename': 'architecture-diagram.png'}
        alt = _build_alt_text(image)
        self.assertIn('아키텍처', alt)
        self.assertIn('다이어그램', alt)

    def test_context_enrichment(self):
        """페이지 문맥에서 관련 문장 보충."""
        image = {'id': 'img3', 'filename': 'flow.png'}
        context = '시스템 흐름도는 데이터 처리 과정을 flow 형태로 보여줍니다.'
        alt = _build_alt_text(image, context)
        self.assertIn('흐름도', alt)

    def test_no_info(self):
        """정보 없는 이미지 처리."""
        image = {'id': 'img4', 'filename': '', 'caption': ''}
        alt = _build_alt_text(image)
        self.assertEqual(alt, '설명 없는 이미지')

    def test_max_length_truncation(self):
        """ALT 텍스트 길이 제한."""
        image = {'id': 'img5', 'filename': 'diagram.png'}
        long_context = ' '.join(['관련 내용이 매우 깁니다 diagram'] * 20) + '.'
        alt = _build_alt_text(image, long_context)
        self.assertLessEqual(len(alt), 130)  # 약간의 여유


class TestValidateAltText(unittest.TestCase):
    """ALT 텍스트 품질 검증 테스트."""

    def test_valid_alt_text(self):
        """올바른 ALT 텍스트는 이슈 없음."""
        issues = validate_alt_text('2024년 분기별 매출 추이를 보여주는 막대 그래프')
        self.assertEqual(issues, [])

    def test_empty_alt_text(self):
        """빈 ALT 텍스트."""
        issues = validate_alt_text('')
        self.assertGreater(len(issues), 0)
        self.assertIn('비어 있습니다', issues[0])

    def test_too_short(self):
        """너무 짧은 ALT 텍스트."""
        issues = validate_alt_text('그래프')
        self.assertTrue(any('짧습니다' in issue for issue in issues))

    def test_too_long(self):
        """너무 긴 ALT 텍스트."""
        long_alt = '매우 상세한 설명 ' * 20
        issues = validate_alt_text(long_alt)
        self.assertTrue(any('깁니다' in issue for issue in issues))

    def test_bad_prefix_korean(self):
        """'이미지'로 시작하는 ALT 텍스트 경고."""
        issues = validate_alt_text('이미지: 매출 차트를 보여주는 그래프입니다')
        self.assertTrue(any('스크린 리더' in issue for issue in issues))

    def test_bad_prefix_english(self):
        """'image of'로 시작하는 ALT 텍스트 경고."""
        issues = validate_alt_text('image of a beautiful sunset over the mountains')
        self.assertTrue(any('스크린 리더' in issue for issue in issues))

    def test_file_extension_included(self):
        """파일 확장자 포함 경고."""
        issues = validate_alt_text('로고 이미지 logo.png 파일')
        self.assertTrue(any('확장자' in issue for issue in issues))

    def test_meaningless_text(self):
        """의미 없는 대체 텍스트 감지."""
        issues = validate_alt_text('이미지')
        self.assertTrue(any('의미 없는' in issue for issue in issues))


class TestCalculateQualityScore(unittest.TestCase):
    """품질 점수 계산 테스트."""

    def test_good_alt_text(self):
        """좋은 ALT 텍스트는 높은 점수."""
        score = _calculate_quality_score('2024년 매출 추이를 보여주는 차트', [])
        self.assertGreaterEqual(score, 80)

    def test_empty_alt_text(self):
        """빈 ALT 텍스트는 0점."""
        score = _calculate_quality_score('', [])
        self.assertEqual(score, 0.0)

    def test_issues_reduce_score(self):
        """이슈가 있으면 점수 감소."""
        score_no_issue = _calculate_quality_score('차트 설명이 포함된 텍스트입니다', [])
        score_with_issue = _calculate_quality_score(
            '차트 설명이 포함된 텍스트입니다',
            ['너무 짧습니다']
        )
        self.assertGreater(score_no_issue, score_with_issue)

    def test_score_range(self):
        """점수는 0~100 범위."""
        score = _calculate_quality_score('테스트', ['이슈1', '이슈2', '이슈3', '이슈4', '이슈5', '이슈6'])
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


class TestGenerateAltTexts(unittest.TestCase):
    """ALT 텍스트 생성 통합 테스트."""

    def test_empty_images(self):
        """빈 이미지 목록."""
        result = generate_alt_texts([])
        self.assertEqual(result, [])

    def test_single_image_with_caption(self):
        """캡션 있는 단일 이미지 처리."""
        images = [{'id': 'img1', 'filename': 'chart.png', 'caption': '월별 매출 추이 그래프'}]
        result = generate_alt_texts(images)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], AltText)
        self.assertEqual(result[0].image_id, 'img1')
        self.assertEqual(result[0].alt_text, '월별 매출 추이 그래프')
        self.assertEqual(result[0].language, 'ko')

    def test_multiple_images(self):
        """여러 이미지 동시 처리."""
        images = [
            {'id': 'img1', 'filename': 'logo.png', 'caption': '회사 로고'},
            {'id': 'img2', 'filename': 'architecture-diagram.png', 'caption': ''},
            {'id': 'img3', 'filename': 'banner-header.jpg', 'caption': '이벤트 배너'},
        ]
        result = generate_alt_texts(images)
        self.assertEqual(len(result), 3)
        # 각 결과에 이슈와 점수가 포함됨
        for alt in result:
            self.assertIsInstance(alt.quality_score, float)
            self.assertIsInstance(alt.issues, list)

    def test_with_page_context(self):
        """페이지 문맥 활용."""
        images = [{'id': 'img1', 'filename': 'flow.png'}]
        context = '데이터 처리 flow 과정을 설명합니다.'
        result = generate_alt_texts(images, page_context=context)
        self.assertEqual(len(result), 1)
        self.assertIn('흐름도', result[0].alt_text)

    def test_quality_score_populated(self):
        """품질 점수가 0~100 범위."""
        images = [{'id': 'img1', 'filename': 'chart.png', 'caption': '연간 매출 성장률 비교 차트'}]
        result = generate_alt_texts(images)
        self.assertGreaterEqual(result[0].quality_score, 0)
        self.assertLessEqual(result[0].quality_score, 100)


if __name__ == '__main__':
    unittest.main()
