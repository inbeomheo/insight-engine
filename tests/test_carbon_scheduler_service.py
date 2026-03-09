"""탄소 스케줄러 서비스 테스트"""
import unittest
from services.carbon_scheduler_service import (
    find_green_slots, schedule_task, calculate_savings,
    TimeSlot, ScheduleDecision
)


class TestCarbonSchedulerService(unittest.TestCase):

    def setUp(self):
        self.slots = [
            TimeSlot('s1', 0, 6, 150.0, 60.0),   # 새벽: 낮은 탄소
            TimeSlot('s2', 6, 12, 300.0, 30.0),   # 오전: 높은 탄소
            TimeSlot('s3', 12, 18, 250.0, 40.0),  # 오후: 중간
            TimeSlot('s4', 18, 24, 100.0, 80.0),  # 저녁: 가장 낮은 탄소
        ]

    def test_find_green_slots(self):
        green = find_green_slots(self.slots, 200.0)
        self.assertEqual(len(green), 2)  # s1, s4

    def test_find_green_slots_none(self):
        green = find_green_slots(self.slots, 50.0)
        self.assertEqual(len(green), 0)

    def test_find_green_slots_all(self):
        green = find_green_slots(self.slots, 500.0)
        self.assertEqual(len(green), 4)

    def test_schedule_task(self):
        decision = schedule_task('ML 학습', 10.0, self.slots)
        self.assertIsInstance(decision, ScheduleDecision)
        self.assertEqual(decision.task_name, 'ML 학습')
        self.assertEqual(decision.recommended_slot.slot_id, 's4')  # 100 g/kWh 최저

    def test_schedule_task_empty_slots(self):
        with self.assertRaises(ValueError):
            schedule_task('task', 1.0, [])

    def test_schedule_task_carbon_saved(self):
        decision = schedule_task('task', 10.0, self.slots)
        # worst=300, best=100, saved=(300-100)*10=2000
        self.assertAlmostEqual(decision.carbon_saved_g, 2000.0)

    def test_calculate_savings(self):
        default = self.slots[1]  # 300 g/kWh
        green = self.slots[3]    # 100 g/kWh
        saved = calculate_savings(default, green, 5.0)
        self.assertAlmostEqual(saved, 1000.0)

    def test_calculate_savings_zero_energy(self):
        saved = calculate_savings(self.slots[0], self.slots[3], 0.0)
        self.assertAlmostEqual(saved, 0.0)

    def test_schedule_task_reason_format(self):
        decision = schedule_task('task', 1.0, self.slots)
        self.assertIn('18시', decision.reason)
        self.assertIn('100.0', decision.reason)

    def test_calculate_savings_same_slot(self):
        saved = calculate_savings(self.slots[0], self.slots[0], 10.0)
        self.assertAlmostEqual(saved, 0.0)


if __name__ == '__main__':
    unittest.main()
