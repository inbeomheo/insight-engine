"""면책 맵 서비스 테스트."""
import unittest
from services.disclaimer_map_service import (
    map_disclaimers,
    insert_mapped_disclaimers,
    DisclaimerTrigger,
)


class TestMapDisclaimers(unittest.TestCase):
    """map_disclaimers 함수 테스트."""

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 빈 결과."""
        self.assertEqual(map_disclaimers(''), [])

    def test_none_content(self):
        """None 입력 시 빈 결과."""
        self.assertEqual(map_disclaimers(None), [])

    def test_blank_content(self):
        """공백만 있는 콘텐츠."""
        self.assertEqual(map_disclaimers('   '), [])

    def test_price_trigger_discount(self):
        """가격 트리거: 할인 언급 탐지."""
        triggers = map_disclaimers('지금 30% 할인 중입니다!')
        price_triggers = [t for t in triggers if t.trigger_type == 'price']
        self.assertGreater(len(price_triggers), 0)

    def test_price_trigger_free(self):
        """가격 트리거: 무료 언급 탐지."""
        triggers = map_disclaimers('무료 체험을 시작하세요.')
        price_triggers = [t for t in triggers if t.trigger_type == 'price']
        self.assertGreater(len(price_triggers), 0)

    def test_price_trigger_won(self):
        """가격 트리거: 원화 금액 탐지."""
        triggers = map_disclaimers('이 제품은 29,900원입니다.')
        price_triggers = [t for t in triggers if t.trigger_type == 'price']
        self.assertGreater(len(price_triggers), 0)

    def test_price_trigger_dollar(self):
        """가격 트리거: 달러 금액 탐지."""
        triggers = map_disclaimers('Only $9.99 per month.')
        price_triggers = [t for t in triggers if t.trigger_type == 'price']
        self.assertGreater(len(price_triggers), 0)

    def test_performance_trigger(self):
        """성능 트리거: 성능 수치 탐지."""
        triggers = map_disclaimers('성능 300% 향상을 달성했습니다.')
        perf_triggers = [t for t in triggers if t.trigger_type == 'performance']
        self.assertGreater(len(perf_triggers), 0)

    def test_guarantee_trigger(self):
        """보증 트리거: 보장 표현 탐지."""
        triggers = map_disclaimers('100% 만족을 보장합니다.')
        guarantee_triggers = [t for t in triggers if t.trigger_type == 'guarantee']
        self.assertGreater(len(guarantee_triggers), 0)

    def test_comparison_trigger(self):
        """비교 트리거: 비교 주장 탐지."""
        triggers = map_disclaimers('업계 최고의 성능을 자랑합니다.')
        comp_triggers = [t for t in triggers if t.trigger_type == 'comparison']
        self.assertGreater(len(comp_triggers), 0)

    def test_no_triggers_clean_content(self):
        """트리거 없는 깨끗한 콘텐츠."""
        triggers = map_disclaimers('오늘 날씨가 좋습니다. 산책을 갔습니다.')
        self.assertEqual(len(triggers), 0)

    def test_trigger_dataclass_fields(self):
        """DisclaimerTrigger 필드 확인."""
        triggers = map_disclaimers('할인 50% 적용!')
        for t in triggers:
            self.assertIsInstance(t, DisclaimerTrigger)
            self.assertTrue(t.trigger_text)
            self.assertIn(t.trigger_type, ['price', 'performance', 'guarantee', 'comparison'])
            self.assertTrue(t.disclaimer_text)
            self.assertIsInstance(t.position, int)
            self.assertIn(t.severity, ['low', 'medium', 'high'])

    def test_sorted_by_position(self):
        """결과가 position 순 정렬."""
        content = '무료 체험 후 29,900원에 구매하세요. 100% 만족 보장합니다.'
        triggers = map_disclaimers(content)
        positions = [t.position for t in triggers]
        self.assertEqual(positions, sorted(positions))

    def test_multiple_trigger_types(self):
        """여러 트리거 타입이 동시에 탐지."""
        content = '무료 체험! 성능 200% 향상! 100% 보장! 업계 최고!'
        triggers = map_disclaimers(content)
        types = {t.trigger_type for t in triggers}
        self.assertGreater(len(types), 1)


class TestInsertMappedDisclaimers(unittest.TestCase):
    """insert_mapped_disclaimers 함수 테스트."""

    def test_no_triggers(self):
        """트리거 없으면 원본 그대로."""
        content = '일반 콘텐츠'
        result = insert_mapped_disclaimers(content, [])
        self.assertEqual(result, content)

    def test_empty_content(self):
        """빈 콘텐츠."""
        result = insert_mapped_disclaimers('', [])
        self.assertEqual(result, '')

    def test_none_content(self):
        """None 콘텐츠."""
        result = insert_mapped_disclaimers(None, [])
        self.assertEqual(result, '')

    def test_disclaimer_appended(self):
        """면책 문구가 콘텐츠 하단에 추가."""
        content = '할인 50% 적용!'
        triggers = map_disclaimers(content)
        result = insert_mapped_disclaimers(content, triggers)
        self.assertIn('---', result)
        self.assertIn('※', result)
        self.assertTrue(result.startswith(content.rstrip()))

    def test_no_duplicate_disclaimers(self):
        """같은 trigger_type의 면책 문구는 중복 삽입되지 않음."""
        content = '할인 50%! 무료 체험! 세일 진행중!'
        triggers = map_disclaimers(content)
        result = insert_mapped_disclaimers(content, triggers)
        # 가격 관련 면책 문구는 하나만 삽입
        price_disclaimer_count = result.count('가격은 변동될 수 있으며')
        self.assertEqual(price_disclaimer_count, 1)

    def test_multiple_type_disclaimers(self):
        """여러 타입의 면책 문구가 각각 삽입."""
        triggers = [
            DisclaimerTrigger('할인', 'price', '※ 가격 면책', 0, 'high'),
            DisclaimerTrigger('보장', 'guarantee', '※ 보증 면책', 10, 'high'),
        ]
        result = insert_mapped_disclaimers('할인 보장 콘텐츠', triggers)
        self.assertIn('※ 가격 면책', result)
        self.assertIn('※ 보증 면책', result)

    def test_highest_severity_wins(self):
        """같은 타입에서 가장 높은 severity의 트리거가 선택."""
        triggers = [
            DisclaimerTrigger('가격', 'price', '※ 가격 면책A', 0, 'low'),
            DisclaimerTrigger('할인', 'price', '※ 가격 면책B', 5, 'high'),
        ]
        result = insert_mapped_disclaimers('가격 할인', triggers)
        # 두 면책 문구가 같은 타입이므로 하나만 삽입
        self.assertIn('---', result)


if __name__ == '__main__':
    unittest.main()
