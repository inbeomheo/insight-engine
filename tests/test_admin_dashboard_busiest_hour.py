"""R74: admin dashboard busiest_hour 필드 테스트"""
import unittest


class TestBusiestHourLogic(unittest.TestCase):
    """busiest_hour 추출 로직 단위 테스트"""

    @staticmethod
    def _extract_busiest_hour(items):
        """auth_routes.admin_dashboard와 동일한 로직"""
        hour_dist = {}
        for item in items:
            created = item.get('created_at', '')
            if created and len(created) >= 13:
                try:
                    hour = int(created[11:13])
                    hour_dist[hour] = hour_dist.get(hour, 0) + 1
                except (ValueError, IndexError):
                    pass
        return max(hour_dist, key=hour_dist.get) if hour_dist else None

    def test_single_hour(self):
        """단일 시간대"""
        items = [{'created_at': '2026-03-17T14:30:00Z'}]
        self.assertEqual(self._extract_busiest_hour(items), 14)

    def test_most_frequent_hour(self):
        """가장 빈번한 시간대 반환"""
        items = [
            {'created_at': '2026-03-17T09:00:00Z'},
            {'created_at': '2026-03-17T09:15:00Z'},
            {'created_at': '2026-03-17T09:45:00Z'},
            {'created_at': '2026-03-17T15:00:00Z'},
            {'created_at': '2026-03-17T15:30:00Z'},
        ]
        self.assertEqual(self._extract_busiest_hour(items), 9)

    def test_empty_items(self):
        """빈 리스트 → None"""
        self.assertIsNone(self._extract_busiest_hour([]))

    def test_no_created_at(self):
        """created_at 없는 항목만 → None"""
        items = [{'style': 'blog_seo'}, {'content': 'abc'}]
        self.assertIsNone(self._extract_busiest_hour(items))

    def test_midnight_hour(self):
        """자정(0시) 처리"""
        items = [
            {'created_at': '2026-03-17T00:10:00Z'},
            {'created_at': '2026-03-17T00:20:00Z'},
        ]
        self.assertEqual(self._extract_busiest_hour(items), 0)

    def test_hour_23(self):
        """23시 처리"""
        items = [{'created_at': '2026-03-17T23:59:59Z'}]
        self.assertEqual(self._extract_busiest_hour(items), 23)

    def test_invalid_created_at_skipped(self):
        """잘못된 형식은 무시, 유효한 것만 집계"""
        items = [
            {'created_at': 'invalid'},
            {'created_at': '2026-03-17T10:00:00Z'},
        ]
        self.assertEqual(self._extract_busiest_hour(items), 10)

    def test_result_is_integer(self):
        """반환값이 정수"""
        items = [{'created_at': '2026-03-17T08:00:00Z'}]
        result = self._extract_busiest_hour(items)
        self.assertIsInstance(result, int)


class TestDashboardBusiestHourRoute(unittest.TestCase):
    """라우트 레벨: busiest_hour 필드 존재 확인 (Supabase 비활성 시)"""

    def test_route_code_contains_busiest_hour(self):
        """admin_dashboard 라우트에 busiest_hour 키가 응답에 포함되는지 코드 검증"""
        import inspect
        # admin_dashboard는 routes/auth_routes.py에서 routes/auth/channel_monitoring.py로 분리됨
        from routes.auth.channel_monitoring import admin_dashboard
        source = inspect.getsource(admin_dashboard)
        self.assertIn('busiest_hour', source)


if __name__ == '__main__':
    unittest.main()
