"""
WebhookService 단위 테스트
- 전송 동작, 비활성화 시 미전송, 에러 격리, 재시도 로직 검증
"""
import unittest
from unittest.mock import patch, MagicMock

from services.platform.webhook_service import WebhookService


class TestWebhookService(unittest.TestCase):
    """WebhookService 동작 검증"""

    @patch('services.platform.webhook_service.requests.post')
    def test_send_calls_requests_post(self, mock_post):
        """send() 호출 시 requests.post가 실행되는지 확인"""
        mock_post.return_value = MagicMock(status_code=200)
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        # _send를 직접 호출 (스레드 대신 동기 테스트)
        svc._send('content.generated', {'title': '테스트'})

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get('json') or call_kwargs[1].get('json')
        self.assertEqual(payload['event'], 'content.generated')
        self.assertEqual(payload['data']['title'], '테스트')
        self.assertIn('timestamp', payload)

    @patch('services.platform.webhook_service.requests.post')
    def test_send_disabled_does_nothing(self, mock_post):
        """enabled=False일 때 전송하지 않음"""
        svc = WebhookService(url='https://example.com/hook', enabled=False)
        svc.send('content.generated', {'title': '테스트'})

        mock_post.assert_not_called()

    @patch('services.platform.webhook_service.requests.post')
    def test_send_empty_url_does_nothing(self, mock_post):
        """URL이 빈 문자열일 때 전송하지 않음"""
        svc = WebhookService(url='', enabled=True)
        svc.send('content.generated', {'title': '테스트'})

        mock_post.assert_not_called()

    @patch('services.platform.webhook_service.requests.post')
    def test_error_does_not_propagate(self, mock_post):
        """전송 실패 시 예외가 전파되지 않음"""
        mock_post.side_effect = Exception('네트워크 오류')
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        # 예외 없이 완료되어야 함
        svc._send('content.generated', {'title': '테스트'})

    @patch('services.platform.webhook_service.requests.post')
    def test_retry_on_first_failure(self, mock_post):
        """첫 번째 실패 후 재시도하는지 확인"""
        mock_post.side_effect = [Exception('첫 번째 실패'), MagicMock(status_code=200)]
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        svc._send('content.generated', {'title': '테스트'})

        self.assertEqual(mock_post.call_count, 2)

    @patch('services.platform.webhook_service.requests.post')
    def test_retry_exhausted(self, mock_post):
        """2번 모두 실패해도 예외 전파 없음"""
        mock_post.side_effect = [Exception('실패1'), Exception('실패2')]
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        # 예외 없이 완료
        svc._send('content.generated', {'title': '테스트'})

        self.assertEqual(mock_post.call_count, 2)

    @patch('services.platform.webhook_service.requests.post')
    def test_test_method_success(self, mock_post):
        """test() 성공 시 결과 반환"""
        mock_post.return_value = MagicMock(status_code=200)
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        result = svc.test()

        self.assertTrue(result['success'])
        self.assertEqual(result['status_code'], 200)

    @patch('services.platform.webhook_service.requests.post')
    def test_test_method_failure(self, mock_post):
        """test() 실패 시 에러 메시지 반환"""
        mock_post.side_effect = Exception('연결 거부')
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        result = svc.test()

        self.assertFalse(result['success'])
        self.assertIn('연결 거부', result['error'])

    def test_test_method_empty_url(self):
        """test() URL 없을 때 에러 반환"""
        svc = WebhookService(url='', enabled=True)

        result = svc.test()

        self.assertFalse(result['success'])
        self.assertIn('URL', result['error'])

    @patch('services.platform.webhook_service.requests.post')
    def test_send_uses_daemon_thread(self, mock_post):
        """send()가 데몬 스레드로 실행되는지 확인"""
        mock_post.return_value = MagicMock(status_code=200)
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        with patch('services.platform.webhook_service.threading.Thread') as mock_thread:
            mock_instance = MagicMock()
            mock_thread.return_value = mock_instance

            svc.send('test', {})

            mock_thread.assert_called_once()
            self.assertTrue(mock_thread.call_args.kwargs.get('daemon'))
            mock_instance.start.assert_called_once()


if __name__ == '__main__':
    unittest.main()
