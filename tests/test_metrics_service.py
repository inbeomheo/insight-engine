"""metrics_service 단위 테스트 (노옵 모드)"""
import unittest

from services import metrics_service


class TestMetricsServiceNoop(unittest.TestCase):
    """prometheus_client 미설치 시 노옵 동작 테스트"""

    def test_record_http_request_no_error(self):
        """HTTP 요청 기록 — 에러 없이 동작"""
        metrics_service.record_http_request('GET', '/api/test', 200, 0.5)

    def test_record_ai_generation_no_error(self):
        """AI 생성 기록 — 에러 없이 동작"""
        metrics_service.record_ai_generation('blog_seo', 'gemini', 'success', 3.0)

    def test_record_ai_generation_failure(self):
        """AI 생성 실패 기록"""
        metrics_service.record_ai_generation('summary', 'deepseek', 'failed', 0.0)

    def test_record_cache_hit(self):
        """캐시 히트 기록"""
        metrics_service.record_cache_hit('ai')

    def test_record_cache_miss(self):
        """캐시 미스 기록"""
        metrics_service.record_cache_miss('ai')

    def test_record_error(self):
        """에러 기록"""
        metrics_service.record_error('timeout', 'ai_service')

    def test_record_transcript_source(self):
        """자막 소스 기록"""
        metrics_service.record_transcript_source('youtube_api')

    def test_get_metrics_output(self):
        """메트릭 출력"""
        data, content_type = metrics_service.get_metrics_output()
        self.assertIsInstance(data, bytes)
        self.assertIn('text/', content_type)

    def test_noop_labels_chainable(self):
        """노옵 객체의 labels() 체이닝"""
        obj = metrics_service.HTTP_REQUESTS_TOTAL
        result = obj.labels(method='GET', endpoint='/')
        result.inc()  # 에러 없어야 함

    def test_noop_set(self):
        """노옵 객체의 set() 호출"""
        metrics_service.ACTIVE_CONNECTIONS.set(5)  # 에러 없어야 함


if __name__ == '__main__':
    unittest.main()
