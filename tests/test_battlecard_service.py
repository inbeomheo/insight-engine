"""battlecard_service 단위 테스트"""
import unittest

from services.battlecard_service import (
    BattleCard,
    RewrittenPost,
    extract_battlecard,
    rewrite_top_post,
    _timestamp_to_display,
    _split_sentences,
    _contains_signal,
    _find_nearby_timestamp,
    _generate_elevator_pitch,
)


# ── 테스트용 자막 데이터 ──
SAMPLE_TRANSCRIPT = """
[00:00] 안녕하세요, 오늘은 우리 제품의 핵심 장점에 대해 이야기하겠습니다.
[00:30] 핵심은 기존 솔루션 대비 3배 빠른 처리 속도입니다. 실제로 고객사 A에서는 처리 시간이 80% 단축되었습니다.
[01:15] 차별화 포인트는 AI 기반 자동 최적화 기능입니다. 다른 제품에는 없는 유일한 기능이죠.
[02:00] 하지만 초기 설정에 시간이 걸릴 수 있습니다. 그래서 우리는 전담 온보딩 팀을 운영합니다.
[02:45] 또한 가격이 높다는 우려가 있을 수 있습니다. 오히려 장기적으로는 TCO가 40% 절감됩니다.
[03:30] 문제는 레거시 시스템과의 호환성입니다. 해결 방안으로 API 브릿지를 제공합니다.
[04:00] 결론은 속도, 자동화, 비용 절감 세 가지가 우리의 경쟁 우위입니다. 데이터가 이를 입증합니다.
"""

SAMPLE_TRANSCRIPT_EN = """
[00:00] Hello, today we'll discuss our key advantages.
[00:30] The key is our processing speed, 3x faster than competitors. Research shows 80% improvement.
[01:15] What makes us unique is our AI-powered optimization. Unlike other tools, we do this automatically.
[02:00] However, there might be concerns about the learning curve. Therefore, we provide dedicated training.
[02:45] The risk is integration complexity. The solution is our comprehensive API.
"""


class TestTimestampToDisplay(unittest.TestCase):
    """_timestamp_to_display 타임스탬프 변환 테스트"""

    def test_mm_ss_format(self):
        """MM:SS 형식 정규화"""
        self.assertEqual(_timestamp_to_display('3:25'), '03:25')

    def test_hh_mm_ss_format(self):
        """HH:MM:SS → 총 분:초 변환"""
        self.assertEqual(_timestamp_to_display('1:02:30'), '62:30')

    def test_zero(self):
        """0:00 처리"""
        self.assertEqual(_timestamp_to_display('0:00'), '00:00')

    def test_already_padded(self):
        """이미 패딩된 형식"""
        self.assertEqual(_timestamp_to_display('05:30'), '05:30')


class TestSplitSentences(unittest.TestCase):
    """_split_sentences 문장 분리 테스트"""

    def test_korean_sentences(self):
        """한국어 문장 분리"""
        result = _split_sentences('첫 번째 문장입니다. 두 번째 문장입니다.')
        self.assertEqual(len(result), 2)

    def test_empty_text(self):
        """빈 텍스트"""
        result = _split_sentences('')
        self.assertEqual(result, [])

    def test_single_sentence(self):
        """단일 문장"""
        result = _split_sentences('하나의 문장입니다.')
        self.assertEqual(len(result), 1)


class TestContainsSignal(unittest.TestCase):
    """_contains_signal 신호어 감지 테스트"""

    def test_korean_signal(self):
        """한국어 신호어 감지"""
        self.assertTrue(_contains_signal('핵심은 이것입니다', ['핵심은', '중요한']))

    def test_no_signal(self):
        """신호어 없음"""
        self.assertFalse(_contains_signal('일반 문장입니다', ['핵심은', '중요한']))

    def test_case_insensitive_english(self):
        """영어 대소문자 무시"""
        self.assertTrue(_contains_signal('The Key Is speed', ['the key is']))


class TestExtractBattlecard(unittest.TestCase):
    """extract_battlecard 배틀카드 추출 테스트"""

    def test_extracts_claims(self):
        """핵심 주장을 추출한다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        self.assertGreater(len(card.claims), 0)
        # "핵심은" 신호어가 있는 주장이 추출되어야 함
        claim_texts = [c['claim'] for c in card.claims]
        has_core_claim = any('핵심' in t or '결론' in t for t in claim_texts)
        self.assertTrue(has_core_claim)

    def test_claims_have_evidence(self):
        """주장에 증거가 포함된다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        # 최소 하나의 주장에 증거가 있어야 함
        has_evidence = any(c['evidence'] for c in card.claims)
        self.assertTrue(has_evidence)

    def test_claims_have_timestamp(self):
        """주장에 타임스탬프가 포함된다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        for claim in card.claims:
            self.assertIn('timestamp', claim)
            self.assertRegex(claim['timestamp'], r'\d{2}:\d{2}')

    def test_minimum_three_objections(self):
        """반론이 최소 3개 이상이다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        self.assertGreaterEqual(len(card.objections), 3)

    def test_objection_has_response(self):
        """반론에 대응이 포함된다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        for obj in card.objections:
            self.assertIn('response', obj)
            self.assertTrue(len(obj['response']) > 0)

    def test_objection_has_source(self):
        """반론에 출처(source)가 포함된다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        for obj in card.objections:
            self.assertIn('source', obj)
            self.assertIn(obj['source'], ('transcript', 'generated'))

    def test_extracts_differentiators(self):
        """차별화 포인트를 추출한다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        self.assertGreater(len(card.key_differentiators), 0)

    def test_elevator_pitch_not_empty(self):
        """엘리베이터 피치가 생성된다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        self.assertTrue(len(card.elevator_pitch) > 0)

    def test_elevator_pitch_max_length(self):
        """엘리베이터 피치가 150자 이내이다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        self.assertLessEqual(len(card.elevator_pitch), 150)

    def test_competitive_advantages(self):
        """경쟁 우위가 추출된다"""
        card = extract_battlecard('test_vid', SAMPLE_TRANSCRIPT)
        self.assertGreater(len(card.competitive_advantages), 0)

    def test_empty_transcript(self):
        """빈 자막이면 빈 배틀카드를 반환한다"""
        card = extract_battlecard('test_vid', '')
        self.assertEqual(card.video_id, 'test_vid')
        self.assertEqual(card.claims, [])
        self.assertEqual(card.objections, [])

    def test_english_transcript(self):
        """영어 자막에서도 추출이 동작한다"""
        card = extract_battlecard('en_vid', SAMPLE_TRANSCRIPT_EN)
        self.assertGreater(len(card.claims), 0)
        self.assertGreaterEqual(len(card.objections), 3)

    def test_video_id_preserved(self):
        """video_id가 결과에 보존된다"""
        card = extract_battlecard('my_video_123', SAMPLE_TRANSCRIPT)
        self.assertEqual(card.video_id, 'my_video_123')

    def test_fallback_objections_when_insufficient(self):
        """반론이 부족하면 생성된 폴백이 추가된다"""
        # 반론 신호어가 없는 자막
        simple_transcript = '핵심은 빠른 속도입니다. 실제로 3배 빠릅니다.'
        card = extract_battlecard('vid', simple_transcript)
        self.assertGreaterEqual(len(card.objections), 3)
        generated = [o for o in card.objections if o['source'] == 'generated']
        self.assertGreater(len(generated), 0)


class TestRewriteTopPost(unittest.TestCase):
    """rewrite_top_post 성과 포스트 재작성 테스트"""

    def test_basic_rewrite(self):
        """기본 재작성이 동작한다"""
        result = rewrite_top_post('테스트 콘텐츠입니다. 좋은 내용이 포함되어 있습니다.')
        self.assertIsInstance(result, RewrittenPost)
        self.assertTrue(len(result.rewritten_content) > 0)

    def test_original_summary(self):
        """원본 요약이 생성된다"""
        content = '짧은 콘텐츠'
        result = rewrite_top_post(content)
        self.assertIn('짧은 콘텐츠', result.original_summary)

    def test_long_original_summary_truncated(self):
        """긴 원본은 200자+...로 잘린다"""
        content = 'A' * 300
        result = rewrite_top_post(content)
        self.assertTrue(result.original_summary.endswith('...'))
        self.assertLessEqual(len(result.original_summary), 204)

    def test_changes_made_not_empty(self):
        """변경 사항 목록이 비어 있지 않다"""
        result = rewrite_top_post('일반적인 콘텐츠입니다. 개선이 필요합니다.')
        self.assertGreater(len(result.changes_made), 0)

    def test_high_bounce_rate_splits_paragraphs(self):
        """높은 이탈률이면 긴 단락을 분리한다"""
        long_para = '내용입니다. ' * 50  # 200자 이상 단락
        result = rewrite_top_post(long_para, {'bounce_rate': 0.7})
        self.assertIn('긴 단락을 분리', ' '.join(result.changes_made))

    def test_low_engagement_adds_cta(self):
        """낮은 참여율이면 CTA를 추가한다"""
        result = rewrite_top_post('테스트 콘텐츠입니다.', {'engagement_rate': 0.1})
        self.assertIn('댓글로 남겨주세요', result.rewritten_content)
        self.assertTrue(any('CTA' in c for c in result.changes_made))

    def test_short_watch_time_adds_summary(self):
        """짧은 시청 시간이면 핵심 요약 박스를 추가한다"""
        content = '핵심은 속도입니다. 결론은 효율성이죠. 다음 내용을 봅시다.'
        result = rewrite_top_post(content, {'avg_watch_time': 60})
        self.assertIn('핵심 요약', result.rewritten_content)

    def test_top_sections_emphasized(self):
        """인기 섹션이 볼드 처리된다"""
        content = '이 섹션은 중요합니다. 다른 내용도 있습니다.'
        result = rewrite_top_post(content, {'top_sections': ['이 섹션은 중요합니다']})
        self.assertIn('**이 섹션은 중요합니다**', result.rewritten_content)

    def test_expected_improvement_calculated(self):
        """개선 기대치가 산정된다"""
        result = rewrite_top_post('콘텐츠', {'bounce_rate': 0.8, 'engagement_rate': 0.1})
        self.assertTrue(len(result.expected_improvement) > 0)
        self.assertIn('예상', result.expected_improvement)

    def test_empty_content(self):
        """빈 콘텐츠 처리"""
        result = rewrite_top_post('')
        self.assertEqual(result.rewritten_content, '')
        self.assertIn('원본 콘텐츠가 없어', result.expected_improvement)

    def test_no_performance_data(self):
        """성과 데이터 없이도 동작한다"""
        result = rewrite_top_post('일반 콘텐츠입니다.')
        self.assertIsInstance(result, RewrittenPost)
        self.assertGreater(len(result.changes_made), 0)

    def test_rewritten_differs_from_original(self):
        """재작성 결과가 원본과 다르다"""
        content = '테스트 콘텐츠입니다. 좋은 결과가 기대됩니다.'
        result = rewrite_top_post(content)
        self.assertNotEqual(result.rewritten_content, content)


class TestGenerateElevatorPitch(unittest.TestCase):
    """_generate_elevator_pitch 엘리베이터 피치 생성 테스트"""

    def test_with_claims_and_diffs(self):
        """주장+차별화로 피치 생성"""
        claims = [{'claim': '속도가 3배 빠릅니다', 'evidence': '테스트 결과'}]
        diffs = ['AI 기반 자동화']
        pitch = _generate_elevator_pitch(claims, diffs)
        self.assertIn('속도가 3배', pitch)

    def test_empty_inputs(self):
        """빈 입력시 안내 메시지"""
        pitch = _generate_elevator_pitch([], [])
        self.assertIn('부족합니다', pitch)

    def test_max_length(self):
        """피치 길이 150자 이내"""
        claims = [{'claim': 'A' * 100, 'evidence': ''}]
        diffs = ['B' * 100]
        pitch = _generate_elevator_pitch(claims, diffs)
        self.assertLessEqual(len(pitch), 150)


if __name__ == '__main__':
    unittest.main()
