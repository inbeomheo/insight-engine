"""
슬라이드 스토리보드 + 프레임 카드 서비스 테스트

generate_storyboard: 5장+ 슬라이드, 각 슬라이드에 제목/불릿/노트/비주얼
create_frame_cards: 3장+ 카드, visual_type/aspect_ratio 유효값
"""
import unittest
from services.storyboard_service import (
    SlideOutline, Storyboard, FrameCard,
    generate_storyboard, create_frame_cards,
    _split_sentences, _contains_signal, _chunk_by_topic,
    _ensure_min_chunks, _extract_bullet_points, _generate_slide_title,
    _suggest_visual, _determine_visual_type, _determine_aspect_ratio,
    _VISUAL_TYPES, _ASPECT_RATIOS,
)


# ── 테스트 자막 데이터 ──
SAMPLE_TRANSCRIPT_KO = (
    "먼저 오늘 주제에 대해 소개하겠습니다. "
    "인공지능이 우리 생활을 어떻게 바꾸고 있는지 살펴보겠습니다. "
    "핵심은 AI가 단순 반복 작업을 자동화한다는 것입니다. "
    "다음으로 구체적인 사례를 살펴보겠습니다. "
    "실제로 제조업에서 AI 도입으로 생산성이 30% 증가했습니다. "
    "또한 의료 분야에서도 AI가 진단 정확도를 높이고 있습니다. "
    "세 번째 주제는 교육 분야입니다. "
    "AI 기반 개인 맞춤 학습이 학생들의 성취도를 향상시킵니다. "
    "네 번째로 윤리적 문제를 다뤄보겠습니다. "
    "하지만 AI의 편향성 문제는 여전히 해결해야 할 과제입니다. "
    "마지막으로 결론을 정리하겠습니다. "
    "요약하면 AI는 기회와 도전을 동시에 가져옵니다."
)

SAMPLE_TRANSCRIPT_EN = (
    "First, let's talk about today's topic. "
    "We'll explore how artificial intelligence is changing our lives. "
    "The key is that AI automates repetitive tasks. "
    "Next, let's look at specific examples. "
    "Research shows that AI adoption increased productivity by 30 percent in manufacturing. "
    "Additionally, AI is improving diagnostic accuracy in healthcare. "
    "Third, education is being transformed. "
    "AI-powered personalized learning improves student achievement. "
    "Finally, let's summarize our findings. "
    "In summary, AI brings both opportunities and challenges."
)

SHORT_TRANSCRIPT = "짧은 텍스트입니다."

STAT_HEAVY_TRANSCRIPT = (
    "매출이 50% 증가했습니다. 비용은 20% 감소했습니다. "
    "투자 대비 수익률은 150%에 달합니다. "
    "사용자 수는 100만 명을 돌파했습니다."
)

QUOTE_HEAVY_TRANSCRIPT = (
    "스티브 잡스가 말했습니다. 'Stay hungry, stay foolish.' "
    "아인슈타인은 '상상력이 지식보다 중요하다'고 했습니다. "
    "마크 트웨인의 명언처럼 '시작하는 비결은 시작하는 것'입니다."
)

TIMESTAMP_TRANSCRIPT = (
    "[0:00] 먼저 오늘 주제를 소개합니다. "
    "[1:30] 다음으로 핵심 내용을 설명합니다. "
    "[3:00] 세 번째 사례를 살펴보겠습니다. "
    "[5:00] 네 번째로 분석 결과입니다. "
    "[7:00] 마지막으로 정리하겠습니다. "
    "요약하면 이것이 결론입니다."
)


class TestSlideOutlineDataclass(unittest.TestCase):
    """SlideOutline 데이터클래스 구조 검증"""

    def test_dataclass_fields(self):
        slide = SlideOutline(slide_number=1, title='테스트')
        self.assertEqual(slide.slide_number, 1)
        self.assertEqual(slide.title, '테스트')
        self.assertIsInstance(slide.bullet_points, list)
        self.assertEqual(slide.speaker_notes, '')
        self.assertEqual(slide.visual_suggestion, '')

    def test_dataclass_with_all_fields(self):
        slide = SlideOutline(
            slide_number=3,
            title='핵심 내용',
            bullet_points=['포인트 1', '포인트 2'],
            speaker_notes='발표자 노트',
            visual_suggestion='차트',
        )
        self.assertEqual(len(slide.bullet_points), 2)
        self.assertEqual(slide.speaker_notes, '발표자 노트')


class TestStoryboardDataclass(unittest.TestCase):
    """Storyboard 데이터클래스 구조 검증"""

    def test_dataclass_fields(self):
        sb = Storyboard(video_id='abc123')
        self.assertEqual(sb.video_id, 'abc123')
        self.assertEqual(sb.total_slides, 0)
        self.assertIsInstance(sb.slides, list)
        self.assertEqual(sb.estimated_duration, 0)


class TestFrameCardDataclass(unittest.TestCase):
    """FrameCard 데이터클래스 구조 검증"""

    def test_dataclass_fields(self):
        card = FrameCard(card_number=1)
        self.assertEqual(card.card_number, 1)
        self.assertEqual(card.headline, '')
        self.assertEqual(card.body_text, '')
        self.assertIn(card.visual_type, _VISUAL_TYPES)
        self.assertIn(card.aspect_ratio, _ASPECT_RATIOS)


class TestHelperFunctions(unittest.TestCase):
    """내부 헬퍼 함수 검증"""

    def test_split_sentences(self):
        text = '첫 문장입니다. 두 번째 문장입니다. 세 번째!'
        result = _split_sentences(text)
        self.assertEqual(len(result), 3)

    def test_split_sentences_empty(self):
        self.assertEqual(_split_sentences(''), [])
        self.assertEqual(_split_sentences('  '), [])

    def test_contains_signal(self):
        self.assertTrue(_contains_signal('다음으로 살펴보겠습니다.', ['다음으로']))
        self.assertFalse(_contains_signal('일반 문장입니다.', ['다음으로']))

    def test_chunk_by_topic(self):
        sentences = [
            '먼저 A를 설명합니다.',
            'A의 세부사항입니다.',
            '다음으로 B를 다룹니다.',
            'B의 세부사항입니다.',
        ]
        chunks = _chunk_by_topic(sentences)
        self.assertGreaterEqual(len(chunks), 2)

    def test_chunk_by_topic_empty(self):
        self.assertEqual(_chunk_by_topic([]), [])

    def test_ensure_min_chunks(self):
        chunks = [['문장 1', '문장 2', '문장 3', '문장 4']]
        result = _ensure_min_chunks(chunks, 3)
        self.assertGreaterEqual(len(result), 3)

    def test_ensure_min_chunks_already_enough(self):
        chunks = [['A'], ['B'], ['C'], ['D'], ['E']]
        result = _ensure_min_chunks(chunks, 5)
        self.assertEqual(len(result), 5)

    def test_extract_bullet_points_with_key_signals(self):
        sentences = [
            '핵심은 효율성입니다.',
            '일반적인 설명입니다.',
            '포인트는 정확성입니다.',
        ]
        bullets = _extract_bullet_points(sentences, max_points=3)
        self.assertGreaterEqual(len(bullets), 1)
        # 핵심 포인트 신호어가 있는 문장이 우선 포함
        self.assertTrue(any('효율' in b for b in bullets))

    def test_generate_slide_title_strips_timestamp(self):
        sentences = ['[1:30] 다음으로 핵심 내용을 설명합니다.']
        title = _generate_slide_title(sentences, 0)
        self.assertNotIn('[1:30]', title)

    def test_suggest_visual_stat(self):
        sentences = ['매출이 50% 증가했습니다.']
        result = _suggest_visual(sentences)
        self.assertIn('차트', result)

    def test_suggest_visual_quote(self):
        sentences = ['스티브 잡스가 말했습니다.']
        result = _suggest_visual(sentences)
        self.assertIn('인용', result)

    def test_determine_visual_type_valid(self):
        for text, expected in [
            ('그가 말했습니다.', 'quote'),
            ('매출 30% 증가.', 'stat'),
            ('- 항목 1 - 항목 2', 'list'),
            ('일반 텍스트입니다.', 'image_placeholder'),
        ]:
            result = _determine_visual_type(text)
            self.assertEqual(result, expected, f"입력: {text}")
            self.assertIn(result, _VISUAL_TYPES)

    def test_determine_aspect_ratio_valid(self):
        for vtype in _VISUAL_TYPES:
            ratio = _determine_aspect_ratio(vtype, 0)
            self.assertIn(ratio, _ASPECT_RATIOS)


class TestGenerateStoryboard(unittest.TestCase):
    """generate_storyboard 함수 통합 테스트"""

    def test_korean_transcript_min_5_slides(self):
        """한국어 자막에서 5장+ 슬라이드 생성"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO, 'vid_ko')
        self.assertIsInstance(result, Storyboard)
        self.assertEqual(result.video_id, 'vid_ko')
        self.assertGreaterEqual(result.total_slides, 5)
        self.assertGreaterEqual(len(result.slides), 5)

    def test_english_transcript_min_5_slides(self):
        """영어 자막에서 5장+ 슬라이드 생성"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_EN, 'vid_en')
        self.assertGreaterEqual(result.total_slides, 5)

    def test_each_slide_has_title(self):
        """각 슬라이드에 제목이 있어야 함"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO)
        for slide in result.slides:
            self.assertIsInstance(slide.title, str)
            self.assertTrue(len(slide.title) > 0)

    def test_each_slide_has_bullet_points(self):
        """각 슬라이드에 불릿 포인트가 있어야 함"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO)
        for slide in result.slides:
            self.assertIsInstance(slide.bullet_points, list)
            self.assertGreaterEqual(len(slide.bullet_points), 1)

    def test_each_slide_has_speaker_notes(self):
        """각 슬라이드에 발표자 노트가 있어야 함"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO)
        for slide in result.slides:
            self.assertIsInstance(slide.speaker_notes, str)
            self.assertTrue(len(slide.speaker_notes) > 0)

    def test_each_slide_has_visual_suggestion(self):
        """각 슬라이드에 비주얼 제안이 있어야 함"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO)
        for slide in result.slides:
            self.assertIsInstance(slide.visual_suggestion, str)
            self.assertTrue(len(slide.visual_suggestion) > 0)

    def test_slide_numbering_sequential(self):
        """슬라이드 번호가 순차적이어야 함"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO)
        for i, slide in enumerate(result.slides):
            self.assertEqual(slide.slide_number, i + 1)

    def test_estimated_duration_positive(self):
        """예상 발표 시간이 양수여야 함"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO)
        self.assertGreater(result.estimated_duration, 0)

    def test_empty_transcript(self):
        """빈 자막도 5장 기본 슬라이드 반환"""
        result = generate_storyboard('', 'empty')
        self.assertIsInstance(result, Storyboard)
        self.assertEqual(result.total_slides, 5)
        self.assertEqual(len(result.slides), 5)

    def test_none_transcript(self):
        """None 자막도 5장 기본 슬라이드 반환"""
        result = generate_storyboard(None, 'none')
        self.assertEqual(result.total_slides, 5)

    def test_whitespace_only_transcript(self):
        """공백만 있는 자막도 기본 슬라이드 반환"""
        result = generate_storyboard('   \n\t  ', 'ws')
        self.assertEqual(result.total_slides, 5)

    def test_short_transcript_still_5_slides(self):
        """짧은 자막도 5장 보장"""
        result = generate_storyboard(SHORT_TRANSCRIPT)
        self.assertGreaterEqual(result.total_slides, 5)

    def test_timestamp_removed_from_content(self):
        """타임스탬프가 불릿/노트에서 제거되어야 함"""
        result = generate_storyboard(TIMESTAMP_TRANSCRIPT)
        for slide in result.slides:
            for bullet in slide.bullet_points:
                self.assertNotRegex(bullet, r'\[\d+:\d+\]')

    def test_total_slides_matches_list_length(self):
        """total_slides와 slides 리스트 길이가 일치해야 함"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO)
        self.assertEqual(result.total_slides, len(result.slides))

    def test_video_id_default_empty(self):
        """video_id 기본값은 빈 문자열"""
        result = generate_storyboard(SAMPLE_TRANSCRIPT_KO)
        self.assertEqual(result.video_id, '')


class TestCreateFrameCards(unittest.TestCase):
    """create_frame_cards 함수 통합 테스트"""

    def test_korean_transcript_min_3_cards(self):
        """한국어 자막에서 3장+ 카드 생성"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO)
        self.assertGreaterEqual(len(result), 3)
        for card in result:
            self.assertIsInstance(card, FrameCard)

    def test_english_transcript_min_3_cards(self):
        """영어 자막에서 3장+ 카드 생성"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_EN)
        self.assertGreaterEqual(len(result), 3)

    def test_visual_type_valid_values(self):
        """visual_type이 유효한 값이어야 함"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO)
        for card in result:
            self.assertIn(card.visual_type, _VISUAL_TYPES)

    def test_aspect_ratio_valid_values(self):
        """aspect_ratio가 유효한 값이어야 함"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO)
        for card in result:
            self.assertIn(card.aspect_ratio, _ASPECT_RATIOS)

    def test_card_numbering_sequential(self):
        """카드 번호가 순차적이어야 함"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO)
        for i, card in enumerate(result):
            self.assertEqual(card.card_number, i + 1)

    def test_each_card_has_headline(self):
        """각 카드에 헤드라인이 있어야 함"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO)
        for card in result:
            self.assertIsInstance(card.headline, str)
            self.assertTrue(len(card.headline) > 0)

    def test_each_card_has_body_text(self):
        """각 카드에 본문 텍스트가 있어야 함"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO)
        for card in result:
            self.assertIsInstance(card.body_text, str)
            self.assertTrue(len(card.body_text) > 0)

    def test_max_cards_limit(self):
        """max_cards 제한 적용"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO, max_cards=3)
        self.assertLessEqual(len(result), 3)
        self.assertGreaterEqual(len(result), 3)

    def test_max_cards_min_3_enforced(self):
        """max_cards < 3 이어도 최소 3장 보장"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO, max_cards=1)
        self.assertGreaterEqual(len(result), 3)

    def test_empty_transcript(self):
        """빈 자막도 3장 기본 카드 반환"""
        result = create_frame_cards('')
        self.assertGreaterEqual(len(result), 3)
        for card in result:
            self.assertIsInstance(card, FrameCard)

    def test_none_transcript(self):
        """None 자막도 3장 기본 카드 반환"""
        result = create_frame_cards(None)
        self.assertGreaterEqual(len(result), 3)

    def test_stat_heavy_uses_stat_type(self):
        """통계가 많은 자막에서 stat 비주얼 타입 사용"""
        result = create_frame_cards(STAT_HEAVY_TRANSCRIPT)
        stat_cards = [c for c in result if c.visual_type == 'stat']
        self.assertGreaterEqual(len(stat_cards), 1)

    def test_quote_heavy_uses_quote_type(self):
        """인용이 많은 자막에서 quote 비주얼 타입 사용"""
        result = create_frame_cards(QUOTE_HEAVY_TRANSCRIPT)
        quote_cards = [c for c in result if c.visual_type == 'quote']
        self.assertGreaterEqual(len(quote_cards), 1)

    def test_stat_card_uses_16_9_ratio(self):
        """stat 타입 카드는 16:9 비율 사용"""
        result = create_frame_cards(STAT_HEAVY_TRANSCRIPT)
        for card in result:
            if card.visual_type == 'stat':
                self.assertEqual(card.aspect_ratio, '16:9')

    def test_large_max_cards(self):
        """큰 max_cards 값도 정상 처리"""
        result = create_frame_cards(SAMPLE_TRANSCRIPT_KO, max_cards=100)
        self.assertGreaterEqual(len(result), 3)
        for card in result:
            self.assertIn(card.visual_type, _VISUAL_TYPES)
            self.assertIn(card.aspect_ratio, _ASPECT_RATIOS)


if __name__ == '__main__':
    unittest.main()
