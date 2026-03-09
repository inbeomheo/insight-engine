"""
구매자 질문 탐색 서비스 테스트
"""
import unittest
from services.buyer_prompt_explorer_service import (
    BuyerPrompt,
    explore_buyer_prompts,
    get_prompts_by_funnel,
    get_prompts_by_intent,
    format_prompts_markdown,
    VALID_INTENTS,
    VALID_FUNNEL_STAGES,
)


class TestBuyerPrompt(unittest.TestCase):
    """BuyerPrompt 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict 변환이 올바른 딕셔너리를 반환한다"""
        prompt = BuyerPrompt(
            question='노트북 추천 순위 비교',
            intent='comparison',
            funnel_stage='consideration',
            priority=0.9,
        )
        result = prompt.to_dict()
        self.assertEqual(result['question'], '노트북 추천 순위 비교')
        self.assertEqual(result['intent'], 'comparison')
        self.assertEqual(result['funnel_stage'], 'consideration')
        self.assertEqual(result['priority'], 0.9)

    def test_to_dict_priority_rounding(self):
        """to_dict에서 priority가 소수점 2자리로 반올림된다"""
        prompt = BuyerPrompt(
            question='테스트', intent='review',
            funnel_stage='awareness', priority=0.8567,
        )
        result = prompt.to_dict()
        self.assertEqual(result['priority'], 0.86)


class TestExploreBuyerPrompts(unittest.TestCase):
    """explore_buyer_prompts 함수 테스트"""

    def test_basic_generation(self):
        """기본 호출 시 5개 이상의 질문을 반환한다"""
        result = explore_buyer_prompts('노트북')
        self.assertGreaterEqual(len(result), 5)
        self.assertIsInstance(result[0], BuyerPrompt)

    def test_category_in_questions(self):
        """카테고리명이 질문에 포함된다"""
        result = explore_buyer_prompts('에어컨')
        for prompt in result:
            self.assertIn('에어컨', prompt.question)

    def test_priority_descending_order(self):
        """결과가 priority 내림차순으로 정렬된다"""
        result = explore_buyer_prompts('마우스')
        priorities = [p.priority for p in result]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_valid_intent_values(self):
        """반환된 모든 prompt의 intent가 유효한 값이다"""
        result = explore_buyer_prompts('키보드')
        for prompt in result:
            self.assertIn(prompt.intent, VALID_INTENTS)

    def test_valid_funnel_stage_values(self):
        """반환된 모든 prompt의 funnel_stage가 유효한 값이다"""
        result = explore_buyer_prompts('모니터')
        for prompt in result:
            self.assertIn(prompt.funnel_stage, VALID_FUNNEL_STAGES)

    def test_priority_range(self):
        """priority가 0~1 범위 내에 있다"""
        result = explore_buyer_prompts('헤드폰')
        for prompt in result:
            self.assertGreaterEqual(prompt.priority, 0.0)
            self.assertLessEqual(prompt.priority, 1.0)

    def test_intent_filter(self):
        """특정 intent만 필터링할 수 있다"""
        result = explore_buyer_prompts('태블릿', intents=['comparison', 'review'])
        intents = {p.intent for p in result}
        self.assertTrue(intents.issubset({'comparison', 'review'}))

    def test_single_intent_filter(self):
        """단일 intent 필터링"""
        result = explore_buyer_prompts('카메라', intents=['howto'])
        for prompt in result:
            self.assertEqual(prompt.intent, 'howto')

    def test_min_priority_filter(self):
        """min_priority 필터 적용 (5개 미만이면 필터 완화)"""
        result = explore_buyer_prompts('스피커', min_priority=0.8)
        # 5개 이상 보장
        self.assertGreaterEqual(len(result), 5)

    def test_max_results_limit(self):
        """max_results로 반환 개수를 제한할 수 있다"""
        result = explore_buyer_prompts('이어폰', max_results=3)
        self.assertEqual(len(result), 3)

    def test_empty_category_raises(self):
        """빈 카테고리는 ValueError를 발생시킨다"""
        with self.assertRaises(ValueError):
            explore_buyer_prompts('')

    def test_whitespace_category_raises(self):
        """공백만 있는 카테고리는 ValueError를 발생시킨다"""
        with self.assertRaises(ValueError):
            explore_buyer_prompts('   ')

    def test_invalid_intent_raises(self):
        """유효하지 않은 intent는 ValueError를 발생시킨다"""
        with self.assertRaises(ValueError):
            explore_buyer_prompts('노트북', intents=['invalid_intent'])

    def test_empty_intents_list_raises(self):
        """빈 intents 리스트는 ValueError를 발생시킨다"""
        with self.assertRaises(ValueError):
            explore_buyer_prompts('노트북', intents=[])

    def test_invalid_min_priority_raises(self):
        """범위 밖 min_priority는 ValueError를 발생시킨다"""
        with self.assertRaises(ValueError):
            explore_buyer_prompts('노트북', min_priority=1.5)
        with self.assertRaises(ValueError):
            explore_buyer_prompts('노트북', min_priority=-0.1)

    def test_category_strip(self):
        """카테고리 앞뒤 공백이 제거된다"""
        result = explore_buyer_prompts('  노트북  ')
        for prompt in result:
            self.assertIn('노트북', prompt.question)
            self.assertNotIn('  노트북  ', prompt.question)

    def test_minimum_five_guarantee(self):
        """높은 min_priority에서도 최소 5개가 반환된다"""
        result = explore_buyer_prompts('냉장고', min_priority=0.99)
        self.assertGreaterEqual(len(result), 5)

    def test_all_intents_generates_full_set(self):
        """모든 intent를 포함하면 5개 이상의 intent별 질문이 생성된다"""
        result = explore_buyer_prompts('세탁기')
        intents = {p.intent for p in result}
        self.assertEqual(intents, VALID_INTENTS)


class TestGetPromptsByFunnel(unittest.TestCase):
    """get_prompts_by_funnel 함수 테스트"""

    def test_groups_by_funnel_stage(self):
        """funnel_stage별로 올바르게 그룹화한다"""
        prompts = explore_buyer_prompts('노트북')
        grouped = get_prompts_by_funnel(prompts)
        self.assertIn('awareness', grouped)
        self.assertIn('consideration', grouped)
        self.assertIn('decision', grouped)

    def test_each_group_sorted_by_priority(self):
        """각 그룹 내에서 priority 내림차순으로 정렬된다"""
        prompts = explore_buyer_prompts('선풍기')
        grouped = get_prompts_by_funnel(prompts)
        for stage, stage_prompts in grouped.items():
            if len(stage_prompts) > 1:
                priorities = [p.priority for p in stage_prompts]
                self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_empty_input(self):
        """빈 입력에 대해 빈 그룹을 반환한다"""
        grouped = get_prompts_by_funnel([])
        self.assertEqual(len(grouped['awareness']), 0)
        self.assertEqual(len(grouped['consideration']), 0)
        self.assertEqual(len(grouped['decision']), 0)


class TestGetPromptsByIntent(unittest.TestCase):
    """get_prompts_by_intent 함수 테스트"""

    def test_groups_by_intent(self):
        """intent별로 올바르게 그룹화한다"""
        prompts = explore_buyer_prompts('의자')
        grouped = get_prompts_by_intent(prompts)
        self.assertGreaterEqual(len(grouped), 1)
        for intent, intent_prompts in grouped.items():
            for p in intent_prompts:
                self.assertEqual(p.intent, intent)

    def test_empty_input(self):
        """빈 입력에 대해 빈 딕셔너리를 반환한다"""
        grouped = get_prompts_by_intent([])
        self.assertEqual(len(grouped), 0)


class TestFormatPromptsMarkdown(unittest.TestCase):
    """format_prompts_markdown 함수 테스트"""

    def test_basic_format(self):
        """마크다운 형식이 올바르게 생성된다"""
        prompts = explore_buyer_prompts('노트북')
        md = format_prompts_markdown(prompts)
        self.assertIn('# 구매자 질문 탐색 결과', md)
        self.assertIn('노트북', md)

    def test_contains_funnel_stages(self):
        """마크다운에 funnel stage 섹션 헤더가 포함된다"""
        prompts = explore_buyer_prompts('태블릿')
        md = format_prompts_markdown(prompts)
        # 적어도 하나의 stage 헤더가 있어야 함
        has_stage = any(
            stage in md
            for stage in ['Awareness', 'Consideration', 'Decision']
        )
        self.assertTrue(has_stage)

    def test_empty_input(self):
        """빈 입력에 대해 빈 문자열을 반환한다"""
        md = format_prompts_markdown([])
        self.assertEqual(md, '')

    def test_contains_priority(self):
        """마크다운에 우선순위 정보가 포함된다"""
        prompts = explore_buyer_prompts('마우스', max_results=3)
        md = format_prompts_markdown(prompts)
        self.assertIn('우선순위:', md)

    def test_contains_intent_labels(self):
        """마크다운에 intent 한국어 라벨이 포함된다"""
        prompts = explore_buyer_prompts('키보드', intents=['comparison'])
        md = format_prompts_markdown(prompts)
        self.assertIn('비교', md)


if __name__ == '__main__':
    unittest.main()
