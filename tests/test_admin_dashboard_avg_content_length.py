"""R54: admin dashboard avg_content_length 필드 테스트"""
import unittest


class TestAvgContentLengthLogic(unittest.TestCase):
    """avg_content_length 계산 로직 단위 테스트"""

    def _calc_avg(self, items):
        """admin_dashboard와 동일한 로직"""
        total_length = 0
        count = 0
        for item in items:
            content = item.get('content') or ''
            if content:
                total_length += len(content)
                count += 1
        return round(total_length / count) if count > 0 else 0

    def test_empty_items(self):
        """항목 없으면 0"""
        self.assertEqual(self._calc_avg([]), 0)

    def test_all_empty_content(self):
        """콘텐츠가 모두 빈 문자열이면 0"""
        items = [{'content': ''}, {'content': None}, {}]
        self.assertEqual(self._calc_avg(items), 0)

    def test_single_item(self):
        """항목 1개의 길이를 그대로 반환"""
        items = [{'content': 'A' * 500}]
        self.assertEqual(self._calc_avg(items), 500)

    def test_multiple_items(self):
        """여러 항목의 평균 계산"""
        items = [{'content': 'A' * 300}, {'content': 'B' * 700}]
        self.assertEqual(self._calc_avg(items), 500)

    def test_mixed_empty_and_filled(self):
        """빈 콘텐츠는 평균 계산에서 제외"""
        items = [{'content': 'A' * 600}, {'content': ''}, {'content': 'B' * 400}]
        self.assertEqual(self._calc_avg(items), 500)

    def test_rounding(self):
        """소수점 반올림"""
        items = [{'content': 'A' * 333}, {'content': 'B' * 334}]
        result = self._calc_avg(items)
        self.assertIsInstance(result, int)
        self.assertEqual(result, 334)  # (333+334)/2 = 333.5 → 334


class TestAdminDashboardAvgContentLength(unittest.TestCase):
    """라우트 레벨: Supabase 비활성 시 동작 확인"""

    def test_route_exists(self):
        """admin_dashboard 라우트에 avg_content_length 코드가 존재하는지 정적 검증"""
        import inspect
        # admin_dashboard는 routes/auth_routes.py에서 routes/auth/channel_monitoring.py로 분리됨
        from routes.auth.channel_monitoring import admin_dashboard
        source = inspect.getsource(admin_dashboard)
        self.assertIn('avg_content_length', source)


if __name__ == '__main__':
    unittest.main()
