"""
WebhookService 단위 테스트
- 전송 동작, 비활성화 시 미전송, 에러 격리, 재시도 로직 검증
"""
import unittest
from unittest.mock import patch, MagicMock

from services.platform.webhook_service import WebhookService, _post_to_resolved_url
from utils.url_safety import ResolvedPublicURL, UnsafeURLError


class TestWebhookService(unittest.TestCase):
    """WebhookService 동작 검증"""

    @patch.object(WebhookService, '_post')
    def test_send_calls_requests_post(self, mock_post):
        """send() 호출 시 고정 IP POST 경로가 실행되는지 확인"""
        mock_post.return_value = MagicMock(status_code=200)
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        # _send를 직접 호출 (스레드 대신 동기 테스트)
        svc._send('content.generated', {'title': '테스트'})

        mock_post.assert_called_once()
        payload = mock_post.call_args.args[0]
        self.assertEqual(payload['event'], 'content.generated')
        self.assertEqual(payload['data']['title'], '테스트')
        self.assertIn('timestamp', payload)

    @patch.object(WebhookService, '_post')
    def test_send_disabled_does_nothing(self, mock_post):
        """enabled=False일 때 전송하지 않음"""
        svc = WebhookService(url='https://example.com/hook', enabled=False)
        svc.send('content.generated', {'title': '테스트'})

        mock_post.assert_not_called()

    @patch.object(WebhookService, '_post')
    def test_send_empty_url_does_nothing(self, mock_post):
        """URL이 빈 문자열일 때 전송하지 않음"""
        svc = WebhookService(url='', enabled=True)
        svc.send('content.generated', {'title': '테스트'})

        mock_post.assert_not_called()

    @patch.object(WebhookService, '_post')
    def test_error_does_not_propagate(self, mock_post):
        """전송 실패 시 예외가 전파되지 않음"""
        mock_post.side_effect = Exception('네트워크 오류')
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        # 예외 없이 완료되어야 함
        svc._send('content.generated', {'title': '테스트'})

    @patch.object(WebhookService, '_post')
    def test_retry_on_first_failure(self, mock_post):
        """첫 번째 실패 후 재시도하는지 확인"""
        mock_post.side_effect = [Exception('첫 번째 실패'), MagicMock(status_code=200)]
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        svc._send('content.generated', {'title': '테스트'})

        self.assertEqual(mock_post.call_count, 2)

    @patch.object(WebhookService, '_post')
    def test_retry_exhausted(self, mock_post):
        """2번 모두 실패해도 예외 전파 없음"""
        mock_post.side_effect = [Exception('실패1'), Exception('실패2')]
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        # 예외 없이 완료
        svc._send('content.generated', {'title': '테스트'})

        self.assertEqual(mock_post.call_count, 2)

    @patch.object(WebhookService, '_post')
    def test_test_method_success(self, mock_post):
        """test() 성공 시 결과 반환"""
        mock_post.return_value = MagicMock(status_code=200)
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        result = svc.test()

        self.assertTrue(result['success'])
        self.assertEqual(result['status_code'], 200)

    @patch.object(WebhookService, '_post')
    def test_test_method_failure(self, mock_post):
        """test() 실패 시 에러 메시지 반환"""
        mock_post.side_effect = Exception('연결 거부')
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        result = svc.test()

        self.assertFalse(result['success'])
        self.assertIn('연결 거부', result['error'])

    def test_test_method_empty_url(self):
        """test() URL 없을 때 에러 반환"""
        svc = WebhookService(url='', enabled=True)

        result = svc.test()

        self.assertFalse(result['success'])
        self.assertIn('URL', result['error'])

    @patch(
        'services.platform.webhook_service.resolve_public_url',
        side_effect=UnsafeURLError('private'),
    )
    @patch('services.platform.webhook_service._post_to_resolved_url')
    def test_test_method_rejects_unsafe_url(self, mock_post, _mock_resolve):
        """test()는 사설망 등 위험 URL에 요청하지 않음"""
        svc = WebhookService(url='http://127.0.0.1/hook', enabled=False)

        result = svc.test()

        self.assertFalse(result['success'])
        self.assertIn('안전하지 않은', result['error'])
        mock_post.assert_not_called()

    @patch('services.platform.webhook_service.resolve_public_url')
    @patch('services.platform.webhook_service._post_to_resolved_url')
    def test_test_method_rejects_redirect(self, mock_post, mock_resolve):
        """test()는 내부망으로 이어질 수 있는 HTTP 리다이렉트를 추적하지 않음"""
        mock_post.return_value = MagicMock(
            status_code=302,
            headers={'Location': 'http://127.0.0.1/admin'},
        )
        mock_resolve.return_value = ResolvedPublicURL(
            'https', 'example.com', 443, '93.184.216.34', '/hook', 'example.com'
        )
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        result = svc.test()

        self.assertFalse(result['success'])
        self.assertIn('리다이렉트', result['error'])

    @patch('services.platform.webhook_service.is_safe_public_url', side_effect=[True, False])
    @patch.object(WebhookService, '_post')
    def test_send_revalidates_url_before_starting_thread(self, mock_post, _mock_safe):
        """send()는 생성 후 DNS 결과가 위험해진 URL도 차단함"""
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        with patch('services.platform.webhook_service.threading.Thread') as mock_thread:
            svc.send('content.generated', {})

        mock_thread.assert_not_called()
        mock_post.assert_not_called()

    @patch('services.platform.webhook_service.resolve_public_url')
    @patch('services.platform.webhook_service._post_to_resolved_url')
    def test_send_rejects_redirect_without_retry(self, mock_post, mock_resolve):
        """실제 send 경로도 리다이렉트를 추적하거나 재시도하지 않음"""
        mock_post.return_value = MagicMock(
            status_code=307,
            headers={'Location': 'http://169.254.169.254/latest/meta-data/'},
        )
        mock_resolve.return_value = ResolvedPublicURL(
            'https', 'example.com', 443, '93.184.216.34', '/hook', 'example.com'
        )
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        svc._send('content.generated', {})

        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(svc.failure_count, 1)

    @patch('services.platform.webhook_service.is_safe_public_url', return_value=True)
    def test_send_uses_daemon_thread(self, _mock_safe):
        """send()가 데몬 스레드로 실행되는지 확인"""
        svc = WebhookService(url='https://example.com/hook', enabled=True)

        with patch('services.platform.webhook_service.threading.Thread') as mock_thread:
            mock_instance = MagicMock()
            mock_thread.return_value = mock_instance

            svc.send('test', {})

            mock_thread.assert_called_once()
            self.assertTrue(mock_thread.call_args.kwargs.get('daemon'))
            mock_instance.start.assert_called_once()

    @patch('utils.url_safety.socket.getaddrinfo')
    @patch('services.platform.webhook_service._post_to_resolved_url')
    def test_post_pins_validated_ip_without_second_dns_lookup(self, mock_post, mock_dns):
        """DNS 응답이 이후 바뀌어도 실제 전송에는 최초 검증 IP만 전달합니다."""
        mock_dns.side_effect = [
            [(2, 1, 6, '', ('93.184.216.34', 443))],
            [(2, 1, 6, '', ('127.0.0.1', 443))],
        ]
        mock_post.return_value = MagicMock(status_code=200)
        svc = WebhookService(url='https://example.com/hook', enabled=False)

        svc._post({'event': 'test'})

        target = mock_post.call_args.args[0]
        self.assertEqual(target.ip, '93.184.216.34')
        self.assertEqual(target.hostname, 'example.com')
        self.assertEqual(mock_dns.call_count, 1)

    @patch('services.platform.webhook_service.http.client.HTTPConnection')
    @patch('services.platform.webhook_service.ssl.create_default_context')
    @patch('services.platform.webhook_service._connect_to_ip')
    def test_https_pinned_connection_preserves_sni_and_host(
        self, mock_connect, mock_context_factory, mock_connection_factory
    ):
        """IP 고정 HTTPS에서도 원래 도메인으로 TLS/HTTP 검증을 수행합니다."""
        target = ResolvedPublicURL(
            'https', 'hooks.example.com', 8443, '2001:4860:4860::8888',
            '/hook?q=1', 'hooks.example.com:8443',
        )
        raw_socket = MagicMock()
        tls_socket = MagicMock()
        mock_connect.return_value = raw_socket
        mock_context_factory.return_value.wrap_socket.return_value = tls_socket
        raw_response = MagicMock(
            status=204,
            reason='No Content',
            getheaders=MagicMock(return_value=[]),
            read=MagicMock(return_value=b''),
        )
        mock_connection_factory.return_value.getresponse.return_value = raw_response

        response = _post_to_resolved_url(target, {'ok': True}, 3)

        self.assertEqual(response.status_code, 204)
        mock_context_factory.return_value.wrap_socket.assert_called_once_with(
            raw_socket,
            server_hostname='hooks.example.com',
        )
        self.assertIs(mock_connection_factory.return_value.sock, tls_socket)
        request_headers = mock_connection_factory.return_value.request.call_args.kwargs['headers']
        self.assertEqual(request_headers['Host'], 'hooks.example.com:8443')
        response.close()  # raw=None인 합성 응답도 정상 종료되어야 합니다.


if __name__ == '__main__':
    unittest.main()
