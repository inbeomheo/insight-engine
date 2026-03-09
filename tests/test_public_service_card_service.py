"""공공서비스 카드 서비스 테스트"""
import unittest
from services.public_service_card_service import (
    create_card, filter_by_category, check_eligibility, format_card, ServiceCard
)


class TestPublicServiceCardService(unittest.TestCase):

    def setUp(self):
        self.card = create_card(
            '청년 취업 지원', 'employment',
            ['만 18~34세', '구직자'], '온라인 신청', '2026-06-30', '☎ 1234-5678'
        )

    def test_create_card(self):
        self.assertIsInstance(self.card, ServiceCard)
        self.assertEqual(self.card.title, '청년 취업 지원')
        self.assertEqual(self.card.category, 'employment')

    def test_create_card_invalid_category(self):
        with self.assertRaises(ValueError):
            create_card('테스트', 'invalid', [], '', None, '')

    def test_create_card_no_deadline(self):
        card = create_card('상시', 'health', [], '방문', None, '')
        self.assertIsNone(card.deadline)

    def test_filter_by_category(self):
        cards = [
            create_card('건강검진', 'health', [], '방문', None, ''),
            self.card,
            create_card('교육', 'education', [], '온라인', None, ''),
        ]
        health = filter_by_category(cards, 'health')
        self.assertEqual(len(health), 1)
        self.assertEqual(health[0].title, '건강검진')

    def test_filter_empty_result(self):
        result = filter_by_category([self.card], 'welfare')
        self.assertEqual(len(result), 0)

    def test_check_eligibility_match(self):
        user = {'tags': ['만 18~34세', '구직자', '서울시민']}
        self.assertTrue(check_eligibility(self.card, user))

    def test_check_eligibility_no_match(self):
        user = {'tags': ['만 18~34세']}
        self.assertFalse(check_eligibility(self.card, user))

    def test_check_eligibility_empty(self):
        card = create_card('누구나', 'welfare', [], '방문', None, '')
        self.assertTrue(check_eligibility(card, {'tags': []}))

    def test_format_card_contains_title(self):
        text = format_card(self.card)
        self.assertIn('청년 취업 지원', text)
        self.assertIn('EMPLOYMENT', text)

    def test_format_card_contains_deadline(self):
        text = format_card(self.card)
        self.assertIn('2026-06-30', text)

    def test_format_card_no_deadline(self):
        card = create_card('상시', 'health', [], '방문', None, '')
        text = format_card(card)
        self.assertNotIn('마감일', text)


if __name__ == '__main__':
    unittest.main()
