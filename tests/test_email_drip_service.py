"""email_drip_service 단위 테스트"""
import unittest

from services.email_drip_service import (
    design_drip,
    DripCampaign,
    DripEmail,
    _calculate_day_schedule,
)


class TestCalculateDaySchedule(unittest.TestCase):

    def test_zero_emails(self):
        self.assertEqual(_calculate_day_schedule(0), [])

    def test_single_email(self):
        result = _calculate_day_schedule(1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], 1)  # 1일차

    def test_five_emails(self):
        result = _calculate_day_schedule(5)
        self.assertEqual(len(result), 5)
        # 오름차순이어야 함
        self.assertEqual(result, sorted(result))

    def test_exceeding_roles(self):
        """역할 수보다 많은 이메일 수 처리"""
        result = _calculate_day_schedule(15)
        self.assertEqual(len(result), 15)
        # 모두 양수
        self.assertTrue(all(d > 0 for d in result))
        # 오름차순
        self.assertEqual(result, sorted(result))


class TestDesignDrip(unittest.TestCase):

    def test_empty_topic(self):
        result = design_drip('')
        self.assertIsInstance(result, DripCampaign)
        self.assertEqual(result.total_emails, 0)
        self.assertEqual(len(result.emails), 0)

    def test_whitespace_topic(self):
        result = design_drip('   ')
        self.assertEqual(result.total_emails, 0)

    def test_default_five_emails(self):
        result = design_drip('Python 입문')
        self.assertEqual(result.total_emails, 5)
        self.assertEqual(len(result.emails), 5)
        self.assertEqual(result.topic, 'Python 입문')

    def test_custom_email_count(self):
        result = design_drip('SEO', num_emails=3)
        self.assertEqual(result.total_emails, 3)
        self.assertEqual(len(result.emails), 3)

    def test_max_email_count_capped(self):
        result = design_drip('토픽', num_emails=50)
        self.assertLessEqual(result.total_emails, 20)

    def test_min_email_count(self):
        result = design_drip('토픽', num_emails=-5)
        self.assertEqual(result.total_emails, 1)

    def test_email_structure(self):
        result = design_drip('마케팅')
        for email in result.emails:
            self.assertIsInstance(email, DripEmail)
            self.assertIsInstance(email.day, int)
            self.assertTrue(email.day > 0)
            self.assertTrue(len(email.subject) > 0)
            self.assertTrue(len(email.body) > 0)
            self.assertTrue(len(email.cta) > 0)

    def test_topic_in_subjects(self):
        result = design_drip('데이터분석')
        for email in result.emails:
            self.assertIn('데이터분석', email.subject)

    def test_topic_in_body(self):
        result = design_drip('AI 활용')
        for email in result.emails:
            self.assertIn('AI 활용', email.body)

    def test_days_ascending(self):
        result = design_drip('테스트', num_emails=5)
        days = [e.day for e in result.emails]
        self.assertEqual(days, sorted(days))

    def test_estimated_days(self):
        result = design_drip('테스트', num_emails=5)
        self.assertGreater(result.estimated_days, 0)
        # 마지막 이메일의 발송일과 일치
        self.assertEqual(result.estimated_days, result.emails[-1].day)

    def test_cycle_suffix_for_many_emails(self):
        """역할 수를 초과하는 이메일은 Part 접미사 포함"""
        result = design_drip('토픽', num_emails=12)
        self.assertEqual(result.total_emails, 12)
        # 9번째 이메일 이후 Part 2 접미사
        has_part = any('Part' in e.subject for e in result.emails)
        self.assertTrue(has_part)


if __name__ == '__main__':
    unittest.main()
