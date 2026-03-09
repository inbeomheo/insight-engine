"""초안 라이브 코치 서비스 테스트."""
import unittest
from services.draft_coach_service import (
    coach_feedback,
    CoachFeedback,
    _analyze_structure,
    _analyze_readability,
    _compute_score,
    _diff_improvements,
)


class TestCoachFeedbackEmpty(unittest.TestCase):
    """빈 입력 처리 테스트."""

    def test_empty_string(self):
        result = coach_feedback('')
        self.assertIsInstance(result, CoachFeedback)
        self.assertEqual(result.overall_score, 0.0)
        self.assertEqual(result.improvements, [])
        self.assertIn('비어', result.summary)

    def test_none_input(self):
        result = coach_feedback(None)
        self.assertEqual(result.overall_score, 0.0)

    def test_whitespace_only(self):
        result = coach_feedback('   \n\t  ')
        self.assertEqual(result.overall_score, 0.0)


class TestAnalyzeStructure(unittest.TestCase):
    """구조 분석 테스트."""

    def test_single_paragraph_long_text(self):
        """긴 텍스트인데 문단이 하나면 구조 부족 피드백."""
        text = '이것은 매우 긴 텍스트입니다. ' * 30
        suggestions = _analyze_structure(text)
        areas = [s['area'] for s in suggestions]
        self.assertIn('구조', areas)

    def test_multiple_paragraphs_no_warning(self):
        """문단이 충분하면 문단 부족 경고 없음."""
        text = ('첫 번째 문단입니다. 충분한 내용이 있습니다.\n\n'
                '두 번째 문단입니다. 역시 충분합니다.\n\n'
                '세 번째 문단입니다. 잘 나뉘어 있습니다.')
        suggestions = _analyze_structure(text)
        para_warnings = [s for s in suggestions
                         if '문단 나누기' in s.get('suggestion', '')]
        self.assertEqual(len(para_warnings), 0)

    def test_no_heading_long_text(self):
        """500자 이상인데 제목이 없으면 경고."""
        text = '내용입니다. 구체적인 설명을 합니다. ' * 40
        suggestions = _analyze_structure(text)
        heading_warnings = [s for s in suggestions
                            if '제목' in s.get('suggestion', '')]
        self.assertGreater(len(heading_warnings), 0)

    def test_with_heading_no_warning(self):
        """제목이 있으면 제목 관련 경고 없음."""
        text = ('# 서론\n\n'
                '내용입니다. 구체적인 설명을 합니다. ' * 40)
        suggestions = _analyze_structure(text)
        heading_warnings = [s for s in suggestions
                            if '제목' in s.get('suggestion', '')
                            and '없습니다' in s.get('suggestion', '')]
        self.assertEqual(len(heading_warnings), 0)

    def test_long_paragraph_warning(self):
        """300자 초과 문단 경고."""
        long_para = '가' * 350
        text = f'{long_para}\n\n짧은 문단입니다. 적절한 길이.'
        suggestions = _analyze_structure(text)
        long_warnings = [s for s in suggestions if '300자' in s.get('suggestion', '')]
        self.assertGreater(len(long_warnings), 0)


class TestAnalyzeReadability(unittest.TestCase):
    """가독성 분석 테스트."""

    def test_long_sentences_warning(self):
        """긴 문장이 과반이면 경고."""
        # 각 문장이 60자를 확실히 넘도록 구성
        long_sent = '가나다라마바사아자차카타파하' * 5  # 70자
        text = f'{long_sent}. {long_sent}. {long_sent}. {long_sent}. {long_sent}.'
        suggestions = _analyze_readability(text)
        long_warnings = [s for s in suggestions if '긴 문장' in s.get('suggestion', '')]
        self.assertGreater(len(long_warnings), 0)

    def test_no_transition_warning(self):
        """전환어가 없고 문장이 5개 이상이면 경고."""
        text = ('첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다. '
                '네 번째 문장입니다. 다섯 번째 문장입니다. 여섯 번째 문장입니다.')
        suggestions = _analyze_readability(text)
        trans_warnings = [s for s in suggestions if '전환어' in s.get('suggestion', '')]
        self.assertGreater(len(trans_warnings), 0)

    def test_forbidden_words_detected(self):
        """금지 표현(과장 수식어) 감지."""
        text = '이것은 놀라운 혁신적 결과입니다. 획기적인 변화가 일어났습니다.'
        suggestions = _analyze_readability(text)
        forbidden_warnings = [s for s in suggestions if '과장' in s.get('suggestion', '')]
        self.assertGreater(len(forbidden_warnings), 0)

    def test_no_forbidden_words(self):
        """금지 표현이 없으면 톤 경고 없음."""
        text = '데이터 분석 결과 처리 속도가 20% 향상되었습니다. 구체적인 수치로 확인할 수 있습니다.'
        suggestions = _analyze_readability(text)
        forbidden_warnings = [s for s in suggestions if '과장' in s.get('suggestion', '')]
        self.assertEqual(len(forbidden_warnings), 0)

    def test_repeated_sentence_start(self):
        """문장 시작어가 3회 이상 반복되면 경고."""
        text = ('이것은 첫 번째입니다. 이것은 두 번째입니다. '
                '이것은 세 번째입니다. 이것은 네 번째입니다.')
        suggestions = _analyze_readability(text)
        repeat_warnings = [s for s in suggestions if '반복' in s.get('suggestion', '')]
        self.assertGreater(len(repeat_warnings), 0)


class TestComputeScore(unittest.TestCase):
    """점수 계산 테스트."""

    def test_empty_text_zero(self):
        self.assertEqual(_compute_score(''), 0.0)

    def test_score_range(self):
        text = '일반적인 텍스트입니다. 충분한 내용이 있습니다.'
        score = _compute_score(text)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_good_structure_higher_score(self):
        """잘 구조화된 글이 더 높은 점수."""
        good = ('# 서론\n\n첫 번째 문단입니다. 내용이 있습니다.\n\n'
                '# 본론\n\n따라서 두 번째 문단입니다. 설명합니다.\n\n'
                '# 결론\n\n또한 세 번째 문단입니다. 마무리합니다.')
        bad = '짧은 글.'
        self.assertGreater(_compute_score(good), _compute_score(bad))

    def test_forbidden_words_lower_score(self):
        """금지 표현이 있으면 점수 감소."""
        clean = '데이터 분석 결과입니다. 수치를 확인하세요.'
        dirty = '놀라운 혁신적 결과입니다. 획기적인 변화입니다.'
        self.assertGreater(_compute_score(clean), _compute_score(dirty))


class TestDiffImprovements(unittest.TestCase):
    """diff 기반 개선점 분석 테스트."""

    def test_added_sentences(self):
        """문장 추가 감지."""
        prev = '첫 번째 문장입니다.'
        curr = '첫 번째 문장입니다. 두 번째 문장이 추가되었습니다. 세 번째 문장도 있습니다.'
        improvements = _diff_improvements(curr, prev)
        added = [i for i in improvements if '추가' in i['suggestion'] and '문장' in i['suggestion']]
        self.assertGreater(len(added), 0)

    def test_added_paragraphs(self):
        """문단 추가 감지."""
        prev = '하나의 문단입니다. 내용이 있습니다.'
        curr = ('하나의 문단입니다. 내용이 있습니다.\n\n'
                '두 번째 문단이 추가되었습니다. 역시 충분한 길이입니다.')
        improvements = _diff_improvements(curr, prev)
        added = [i for i in improvements if '문단' in i['suggestion'] and '추가' in i['suggestion']]
        self.assertGreater(len(added), 0)

    def test_added_transitions(self):
        """전환어 추가 감지."""
        prev = '첫 번째 내용입니다. 두 번째 내용입니다.'
        curr = '첫 번째 내용입니다. 따라서 두 번째 결론에 도달합니다.'
        improvements = _diff_improvements(curr, prev)
        trans = [i for i in improvements if '전환어' in i['suggestion']]
        self.assertGreater(len(trans), 0)

    def test_reduced_forbidden(self):
        """금지 표현 감소 감지."""
        prev = '놀라운 혁신적 결과입니다. 획기적인 변화입니다.'
        curr = '데이터 분석 결과입니다. 구체적인 변화입니다.'
        improvements = _diff_improvements(curr, prev)
        tone = [i for i in improvements if '과장' in i['suggestion'] and '줄어' in i['suggestion']]
        self.assertGreater(len(tone), 0)

    def test_no_diff_no_items(self):
        """동일 텍스트면 diff 항목 없음."""
        text = '동일한 텍스트입니다. 변화가 없습니다.'
        improvements = _diff_improvements(text, text)
        self.assertEqual(len(improvements), 0)


class TestCoachFeedbackIntegration(unittest.TestCase):
    """통합 테스트."""

    def test_returns_coach_feedback_type(self):
        result = coach_feedback('테스트 초안입니다. 내용이 있습니다.')
        self.assertIsInstance(result, CoachFeedback)

    def test_improvements_at_least_three_with_diff(self):
        """diff 모드에서 피드백 3개 이상 반환 (완료 조건)."""
        prev = '짧은 글.'
        curr = ('# 서론\n\n첫 번째 문단입니다. 내용을 설명합니다.\n\n'
                '따라서 두 번째 문단이 이어집니다. 상세한 분석을 합니다.\n\n'
                '# 결론\n\n또한 세 번째 문단에서 마무리합니다. 정리하겠습니다.')
        result = coach_feedback(curr, prev)
        self.assertGreaterEqual(len(result.improvements), 3)

    def test_score_delta_positive_on_improvement(self):
        """개선 시 score_delta 양수."""
        prev = '짧은 글.'
        curr = ('# 제목\n\n첫 번째 문단입니다. 설명합니다.\n\n'
                '따라서 두 번째 문단입니다. 결론을 내립니다.\n\n'
                '또한 세 번째 문단입니다. 마무리합니다.')
        result = coach_feedback(curr, prev)
        self.assertGreater(result.score_delta, 0)

    def test_priority_ordering(self):
        """improvements가 priority 순서로 정렬되는지 확인."""
        text = '놀라운 혁신적 결과입니다. ' * 30  # 금지 표현(high) + 구조 문제
        result = coach_feedback(text)
        if len(result.improvements) >= 2:
            priorities = [i['priority'] for i in result.improvements]
            order = {'high': 0, 'medium': 1, 'low': 2}
            numeric = [order[p] for p in priorities]
            self.assertEqual(numeric, sorted(numeric))

    def test_summary_mentions_score(self):
        """summary에 점수가 포함되는지 확인."""
        result = coach_feedback('일반적인 텍스트입니다. 충분한 내용이 있습니다.')
        self.assertIn('점', result.summary)

    def test_no_previous_draft_zero_delta(self):
        """previous_draft 없으면 score_delta는 0."""
        result = coach_feedback('일반적인 텍스트입니다.')
        self.assertEqual(result.score_delta, 0.0)

    def test_improvement_areas_valid(self):
        """모든 improvement의 area가 유효한 값인지 확인."""
        text = '놀라운 결과입니다. ' * 20
        result = coach_feedback(text)
        valid_areas = {'구조', '가독성', '키워드', '톤'}
        for item in result.improvements:
            self.assertIn(item['area'], valid_areas)

    def test_improvement_priorities_valid(self):
        """모든 improvement의 priority가 유효한 값인지 확인."""
        text = '놀라운 결과입니다. ' * 20
        result = coach_feedback(text)
        valid_priorities = {'high', 'medium', 'low'}
        for item in result.improvements:
            self.assertIn(item['priority'], valid_priorities)


if __name__ == '__main__':
    unittest.main()
