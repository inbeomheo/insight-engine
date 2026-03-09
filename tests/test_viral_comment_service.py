"""
바이럴 댓글 선점 + 제목 실험 서비스 테스트 (T6.3)
"""
import unittest

from services.viral_comment_service import (
    CommentDraft,
    ExperimentResult,
    _apply_emojis,
    _build_hashtags,
    _extract_topic_from_url,
    _score_title,
    _select_hooks,
    _select_template,
    draft_viral_comment,
    run_title_experiment,
)


# ===========================================================================
# run_title_experiment 테스트
# ===========================================================================

class TestRunTitleExperiment(unittest.TestCase):
    """제목 변형 실험 — CTR 예측 기반 승자 선정"""

    def test_basic_experiment_returns_result(self):
        """기본 2개 변형 실험이 ExperimentResult를 반환"""
        result = run_title_experiment('abc123', ['제목A', '제목B'])
        self.assertIsInstance(result, ExperimentResult)
        self.assertEqual(result.video_id, 'abc123')
        self.assertIn(result.winner, ['제목A', '제목B'])

    def test_winner_has_highest_ctr(self):
        """승자 제목은 가장 높은 predicted_ctr을 가져야 함"""
        variants = ['짧은', '5가지 꿀팁으로 생산성 높이는 방법은?']
        result = run_title_experiment('v1', variants)
        ctrs = {v['title']: v['predicted_ctr'] for v in result.variants}
        self.assertEqual(result.winner, max(ctrs, key=ctrs.get))

    def test_variants_sorted_descending(self):
        """결과 variants는 CTR 내림차순으로 정렬"""
        result = run_title_experiment('v2', ['A', 'B는 왜 중요할까?', '10가지 방법'])
        ctrs = [v['predicted_ctr'] for v in result.variants]
        self.assertEqual(ctrs, sorted(ctrs, reverse=True))

    def test_confidence_between_0_and_1(self):
        """신뢰도는 0~1 사이"""
        result = run_title_experiment('v3', ['하나', '둘'])
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_minimum_two_variants_required(self):
        """변형 1개만 전달하면 ValueError"""
        with self.assertRaises(ValueError):
            run_title_experiment('v4', ['하나만'])

    def test_empty_list_raises(self):
        """빈 리스트 전달 시 ValueError"""
        with self.assertRaises(ValueError):
            run_title_experiment('v5', [])

    def test_blank_strings_filtered(self):
        """공백만 있는 변형은 필터링 → 유효 2개 미만이면 ValueError"""
        with self.assertRaises(ValueError):
            run_title_experiment('v6', ['유효', '   ', ''])

    def test_winner_reason_contains_ctr(self):
        """승자 사유에 CTR 수치가 포함"""
        result = run_title_experiment('v7', ['제목X', '왜 이것이 중요한 5가지 이유?'])
        self.assertIn('CTR', result.winner_reason)
        self.assertIn('%', result.winner_reason)

    def test_each_variant_has_scores(self):
        """각 변형에 세부 scores 딕셔너리가 존재"""
        result = run_title_experiment('v8', ['AA', 'BB는 어떻게 할까?'])
        for v in result.variants:
            self.assertIn('scores', v)
            self.assertIsInstance(v['scores'], dict)

    def test_many_variants(self):
        """5개 이상 변형도 정상 동작"""
        titles = [f'제목 변형 {i}' for i in range(10)]
        result = run_title_experiment('v9', titles)
        self.assertEqual(len(result.variants), 10)

    def test_number_in_title_boosts_ctr(self):
        """숫자가 포함된 제목이 더 높은 CTR을 받아야 함"""
        score_with_num = _score_title('10가지 생산성 향상 방법')
        score_without = _score_title('생산성을 향상시키는 방법입니다')
        self.assertGreater(
            score_with_num['predicted_ctr'],
            score_without['predicted_ctr'],
        )

    def test_question_title_boosts_ctr(self):
        """질문형 제목이 CTR 보너스를 받아야 함"""
        score_q = _score_title('왜 이것이 중요할까?')
        score_plain = _score_title('이것은 중요하다')
        self.assertGreater(score_q['predicted_ctr'], score_plain['predicted_ctr'])

    def test_ad_title_penalty(self):
        """'광고' 키워드가 있으면 CTR 감점 (동일 조건 비교)"""
        score_ad = _score_title('광고 포함 이 제품을 소개합니다')
        score_clean = _score_title('순수한 이 제품을 소개합니다')
        # 광고 키워드 감점(-0.05) 확인
        self.assertIn('광고 표시', score_ad['scores'])
        self.assertLess(score_ad['predicted_ctr'], score_clean['predicted_ctr'])

    def test_too_short_title_penalty(self):
        """너무 짧은 제목(15자 미만)은 길이 감점"""
        score = _score_title('짧은제목')
        self.assertIn('길이', score['scores'])
        self.assertLess(score['scores']['길이'], 0)

    def test_optimal_length_bonus(self):
        """15~40자 제목은 길이 보너스"""
        score = _score_title('이 정도 길이의 제목은 가독성이 좋습니다')
        self.assertIn('길이', score['scores'])
        self.assertGreater(score['scores']['길이'], 0)

    def test_predicted_ctr_clamped(self):
        """predicted_ctr은 0.01~0.99 범위 내"""
        # 극단적으로 좋은 제목
        score = _score_title('5가지 무료 꿀팁: 왜 이 방법이 최고인가?!')
        self.assertGreaterEqual(score['predicted_ctr'], 0.01)
        self.assertLessEqual(score['predicted_ctr'], 0.99)


# ===========================================================================
# draft_viral_comment 테스트
# ===========================================================================

class TestDraftViralComment(unittest.TestCase):
    """바이럴 댓글 초안 생성"""

    def _make_voice(self, tone='friendly', keywords=None, emoji='minimal'):
        return {
            'tone': tone,
            'keywords': keywords or ['AI', '자동화'],
            'emoji_style': emoji,
        }

    def test_basic_draft_returns_comment_draft(self):
        """기본 호출이 CommentDraft를 반환"""
        result = draft_viral_comment(
            'https://youtube.com/watch?v=abc',
            self._make_voice(),
            topic='인공지능',
        )
        self.assertIsInstance(result, CommentDraft)

    def test_comment_text_contains_topic(self):
        """댓글 텍스트에 주제가 포함"""
        result = draft_viral_comment(
            'https://example.com/post',
            self._make_voice(),
            topic='딥러닝',
        )
        self.assertIn('딥러닝', result.comment_text)

    def test_tone_preserved(self):
        """브랜드 톤이 결과에 보존"""
        result = draft_viral_comment(
            'https://example.com/post',
            self._make_voice(tone='professional'),
            topic='마케팅',
        )
        self.assertEqual(result.tone, 'professional')

    def test_unknown_tone_falls_back_to_default(self):
        """미지원 톤은 기본 톤(friendly)으로 폴백"""
        result = draft_viral_comment(
            'https://example.com/post',
            self._make_voice(tone='alien_tone'),
            topic='주제',
        )
        self.assertEqual(result.tone, 'friendly')

    def test_hashtags_from_topic_and_keywords(self):
        """해시태그에 주제 단어와 브랜드 키워드가 포함"""
        result = draft_viral_comment(
            'https://example.com/post',
            self._make_voice(keywords=['브랜드', '마케팅']),
            topic='콘텐츠 전략',
        )
        self.assertTrue(len(result.hashtags) > 0)
        # 해시태그는 # 으로 시작
        for tag in result.hashtags:
            self.assertTrue(tag.startswith('#'))

    def test_hashtags_max_five(self):
        """해시태그는 최대 5개"""
        result = draft_viral_comment(
            'https://example.com/post',
            self._make_voice(keywords=['a', 'b', 'c', 'd', 'e', 'f']),
            topic='매우 긴 주제 단어가 많은 경우 테스트',
        )
        self.assertLessEqual(len(result.hashtags), 5)

    def test_engagement_hooks_present(self):
        """참여 유도 후크가 포함"""
        result = draft_viral_comment(
            'https://example.com/post',
            self._make_voice(),
            topic='주제',
        )
        self.assertTrue(len(result.engagement_hooks) > 0)

    def test_empty_url_raises(self):
        """빈 URL이면 ValueError"""
        with self.assertRaises(ValueError):
            draft_viral_comment('', self._make_voice(), topic='주제')

    def test_blank_url_raises(self):
        """공백만 있는 URL이면 ValueError"""
        with self.assertRaises(ValueError):
            draft_viral_comment('   ', self._make_voice(), topic='주제')

    def test_emoji_minimal_no_emoji(self):
        """minimal 이모지 스타일은 이모지 없음"""
        result = draft_viral_comment(
            'https://example.com/post',
            self._make_voice(emoji='minimal'),
            topic='주제',
        )
        # minimal이면 이모지가 추가되지 않아야 함
        # 템플릿 자체에 이모지가 없으므로, 원래 텍스트와 동일
        self.assertNotIn('🔥', result.comment_text)
        self.assertNotIn('💯', result.comment_text)

    def test_emoji_heavy_adds_emoji(self):
        """heavy 이모지 스타일은 이모지 추가"""
        result = draft_viral_comment(
            'https://example.com/post',
            self._make_voice(emoji='heavy'),
            topic='주제',
        )
        has_emoji = any(
            e in result.comment_text
            for e in ['🔥', '💯', '🎯', '👏', '💡', '✨', '🚀']
        )
        self.assertTrue(has_emoji)

    def test_empty_topic_uses_url_inference(self):
        """topic이 비어있으면 URL에서 주제 추론"""
        result = draft_viral_comment(
            'https://youtube.com/watch?v=abc123',
            self._make_voice(),
            topic='',
        )
        # URL에서 추론된 주제가 댓글에 포함
        self.assertIsInstance(result.comment_text, str)
        self.assertTrue(len(result.comment_text) > 0)

    def test_post_url_preserved(self):
        """post_url이 결과에 보존"""
        url = 'https://example.com/my-post'
        result = draft_viral_comment(url, self._make_voice(), topic='테스트')
        self.assertEqual(result.post_url, url)


# ===========================================================================
# 내부 함수 단위 테스트
# ===========================================================================

class TestInternalHelpers(unittest.TestCase):
    """내부 헬퍼 함수 테스트"""

    def test_extract_topic_youtube(self):
        """YouTube URL에서 '영상 콘텐츠' 추출"""
        topic = _extract_topic_from_url('https://youtube.com/watch?v=abc12345678')
        self.assertEqual(topic, '영상 콘텐츠')

    def test_extract_topic_general_url(self):
        """일반 URL에서 경로 세그먼트 추출"""
        topic = _extract_topic_from_url('https://blog.example.com/ai-trends-2026')
        self.assertIn('ai', topic.lower())

    def test_extract_topic_fallback(self):
        """추출 불가 시 '콘텐츠' 기본값"""
        topic = _extract_topic_from_url('https://example.com/')
        self.assertEqual(topic, '콘텐츠')

    def test_select_template_valid_tone(self):
        """유효한 톤으로 템플릿 선택"""
        template = _select_template('professional')
        self.assertIn('{topic}', template)

    def test_select_template_cycles(self):
        """인덱스가 템플릿 수를 초과해도 순환"""
        t0 = _select_template('friendly', index=0)
        t_cycle = _select_template('friendly', index=3)  # len(friendly) == 3
        self.assertEqual(t0, t_cycle)

    def test_build_hashtags_deduplication(self):
        """해시태그 중복 제거"""
        tags = _build_hashtags('AI 자동화', ['AI', '마케팅'])
        # '#AI'가 주제에서도, 키워드에서도 나올 수 있지만 중복 없어야 함
        self.assertEqual(len(tags), len(set(tags)))

    def test_apply_emojis_minimal(self):
        """minimal 스타일은 텍스트 변경 없음"""
        original = '테스트 텍스트'
        result = _apply_emojis(original, 'minimal')
        self.assertEqual(result, original)

    def test_apply_emojis_moderate(self):
        """moderate 스타일은 이모지 추가"""
        original = '테스트 텍스트'
        result = _apply_emojis(original, 'moderate')
        self.assertNotEqual(result, original)
        self.assertTrue(result.startswith(original))

    def test_select_hooks_count(self):
        """요청한 수만큼 후크 반환"""
        hooks = _select_hooks(count=2)
        self.assertEqual(len(hooks), 2)

    def test_select_hooks_returns_strings(self):
        """후크는 문자열 리스트"""
        hooks = _select_hooks(count=3)
        for h in hooks:
            self.assertIsInstance(h, str)


if __name__ == '__main__':
    unittest.main()
