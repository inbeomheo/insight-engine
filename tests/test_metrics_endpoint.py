"""/metrics Prometheus 엔드포인트 테스트"""
import re
import unittest
from unittest.mock import patch


class TestMetricsEndpoint(unittest.TestCase):
    """Prometheus text format + 인증 토큰 검증"""

    def _client(self):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_metrics_returns_prometheus_text_format(self, _mock_sb):
        resp = self._client().get('/metrics')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/plain', resp.headers['Content-Type'])
        body = resp.get_data(as_text=True)
        # 필수 지표 존재 확인
        for metric in (
            'insight_requests_total',
            'insight_errors_total',
            'insight_error_rate',
            'insight_active_requests',
            'insight_build_info',
        ):
            self.assertIn(metric, body, f"지표 {metric} 누락")
        # HELP/TYPE 헤더 포함
        self.assertIn('# HELP insight_requests_total', body)
        self.assertIn('# TYPE insight_requests_total counter', body)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_metrics_includes_queue_status(self, _mock_sb):
        resp = self._client().get('/metrics')
        body = resp.get_data(as_text=True)
        # 큐 상태별 라벨 존재
        for status in ('queued', 'publishing', 'success', 'failed'):
            self.assertIn(f'insight_publish_queue_items{{status="{status}"}}', body)

    @patch.dict('os.environ', {'METRICS_AUTH_TOKEN': 'secret123'}, clear=False)
    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_metrics_requires_token_when_configured(self, _mock_sb):
        """METRICS_AUTH_TOKEN 설정 시 토큰 없으면 401"""
        client = self._client()
        resp = client.get('/metrics')
        self.assertEqual(resp.status_code, 401)

        # 올바른 토큰 → 200
        resp_ok = client.get('/metrics', headers={'Authorization': 'Bearer secret123'})
        self.assertEqual(resp_ok.status_code, 200)

        # 잘못된 토큰 → 401
        resp_bad = client.get('/metrics', headers={'Authorization': 'Bearer wrong'})
        self.assertEqual(resp_bad.status_code, 401)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_metrics_values_are_numeric(self, _mock_sb):
        """모든 지표 값이 숫자(int/float)인지 확인 — Prometheus 파싱 가능"""
        resp = self._client().get('/metrics')
        body = resp.get_data(as_text=True)
        for line in body.splitlines():
            if not line or line.startswith('#'):
                continue
            # 메트릭 이름과 값 분리: "name{labels} value" 또는 "name value"
            match = re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(?:\{[^}]*\})?\s+(.+)$', line)
            self.assertIsNotNone(match, f"파싱 불가 라인: {line}")
            value = match.group(1).strip()
            try:
                float(value)
            except ValueError:
                self.fail(f"숫자가 아닌 값: '{value}' (라인: {line})")


if __name__ == '__main__':
    unittest.main()
