"""웹훅 SSRF 방어 강화 테스트 — is_safe_public_url, is_dangerous_ip"""
import unittest
from unittest.mock import MagicMock, patch
import ipaddress

import requests

from utils.url_safety import (
    PublicFetchTooLarge,
    ResolvedPublicURL,
    UnsafeURLError,
    _read_bounded_body,
    fetch_public_url,
    is_dangerous_ip,
    is_safe_public_url,
    resolve_public_url,
)


class TestIsDangerousIp(unittest.TestCase):
    """is_dangerous_ip 함수 테스트"""

    def test_loopback_v4(self):
        self.assertTrue(is_dangerous_ip(ipaddress.ip_address('127.0.0.1')))

    def test_loopback_v6(self):
        self.assertTrue(is_dangerous_ip(ipaddress.ip_address('::1')))

    def test_private_10(self):
        self.assertTrue(is_dangerous_ip(ipaddress.ip_address('10.0.0.1')))

    def test_private_192(self):
        self.assertTrue(is_dangerous_ip(ipaddress.ip_address('192.168.1.1')))

    def test_link_local(self):
        self.assertTrue(is_dangerous_ip(ipaddress.ip_address('169.254.169.254')))

    def test_ipv4_mapped_v6_private(self):
        """::ffff:127.0.0.1 같은 IPv4-mapped IPv6 차단"""
        self.assertTrue(is_dangerous_ip(ipaddress.ip_address('::ffff:127.0.0.1')))

    def test_ipv4_mapped_v6_private_192(self):
        self.assertTrue(is_dangerous_ip(ipaddress.ip_address('::ffff:192.168.0.1')))

    def test_public_ip_safe(self):
        self.assertFalse(is_dangerous_ip(ipaddress.ip_address('8.8.8.8')))

    def test_public_v6_safe(self):
        self.assertFalse(is_dangerous_ip(ipaddress.ip_address('2001:4860:4860::8888')))


class TestValidateWebhookUrl(unittest.TestCase):
    """is_safe_public_url SSRF 방어 테스트"""

    def test_public_https_allowed(self):
        self.assertTrue(is_safe_public_url('https://hooks.slack.com/services/T123'))

    def test_http_allowed(self):
        self.assertTrue(is_safe_public_url('http://example.com/hook'))

    def test_ftp_blocked(self):
        self.assertFalse(is_safe_public_url('ftp://example.com/file'))

    def test_empty_url(self):
        self.assertFalse(is_safe_public_url(''))

    def test_no_scheme(self):
        self.assertFalse(is_safe_public_url('example.com/hook'))

    def test_localhost_blocked(self):
        self.assertFalse(is_safe_public_url('http://localhost:8080/hook'))

    def test_127_blocked(self):
        self.assertFalse(is_safe_public_url('http://127.0.0.1/hook'))

    def test_private_10_blocked(self):
        self.assertFalse(is_safe_public_url('http://10.0.0.1/hook'))

    def test_private_192_blocked(self):
        self.assertFalse(is_safe_public_url('http://192.168.1.1/hook'))

    def test_metadata_google_blocked(self):
        """GCP 메타데이터 엔드포인트 차단"""
        self.assertFalse(is_safe_public_url('http://metadata.google.internal/computeMetadata/v1/'))

    def test_aws_metadata_ip_blocked(self):
        """AWS 메타데이터 엔드포인트(169.254.169.254) 차단"""
        self.assertFalse(is_safe_public_url('http://169.254.169.254/latest/meta-data/'))

    def test_ipv6_loopback_blocked(self):
        """IPv6 루프백 [::1] 차단"""
        self.assertFalse(is_safe_public_url('http://[::1]/hook'))

    def test_ipv4_mapped_v6_blocked(self):
        """IPv4-mapped IPv6 ::ffff:127.0.0.1 차단"""
        self.assertFalse(is_safe_public_url('http://[::ffff:127.0.0.1]/hook'))

    @patch('utils.url_safety.socket.getaddrinfo')
    def test_dns_resolving_to_private_blocked(self, mock_getaddrinfo):
        """도메인이 사설 IP로 해석되면 차단 (DNS 리바인딩 방어)"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('127.0.0.1', 80))
        ]
        self.assertFalse(is_safe_public_url('https://evil.example.com/hook'))

    @patch('utils.url_safety.socket.getaddrinfo')
    def test_dns_resolving_to_public_allowed(self, mock_getaddrinfo):
        """도메인이 공개 IP로 해석되면 허용"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('93.184.216.34', 443))
        ]
        self.assertTrue(is_safe_public_url('https://example.com/hook'))

    @patch('utils.url_safety.socket.getaddrinfo')
    def test_dns_failure_blocked(self, mock_getaddrinfo):
        """DNS 해석 실패 (존재하지 않는 도메인)은 차단"""
        import socket
        mock_getaddrinfo.side_effect = socket.gaierror('Name not found')
        self.assertFalse(is_safe_public_url('https://nonexistent.invalid/hook'))

    def test_zero_ip_blocked(self):
        """0.0.0.0 차단"""
        self.assertFalse(is_safe_public_url('http://0.0.0.0/hook'))


class TestPublicUrlFetch(unittest.TestCase):
    @patch('utils.url_safety.socket.getaddrinfo')
    def test_iri_path_query_are_percent_encoded(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, '', ('93.184.216.34', 443))]

        target = resolve_public_url(
            'https://예시.한국/문서/한 글?q=검색어&next=%2fkeep#fragment'
        )

        self.assertEqual(target.hostname, 'xn--vv4b11d.xn--3e0b707e')
        self.assertEqual(
            target.request_target,
            '/%EB%AC%B8%EC%84%9C/%ED%95%9C%20%EA%B8%80'
            '?q=%EA%B2%80%EC%83%89%EC%96%B4&next=%2Fkeep',
        )

    @patch('utils.url_safety.socket.getaddrinfo')
    def test_url_credentials_are_rejected_before_dns(self, mock_dns):
        with self.assertRaises(UnsafeURLError):
            resolve_public_url('https://user:secret@example.com/private')
        mock_dns.assert_not_called()

    @patch('utils.url_safety._get_from_public_target')
    @patch('utils.url_safety.resolve_public_url')
    def test_redirect_is_resolved_and_pinned_again(self, mock_resolve, mock_get):
        first = ResolvedPublicURL(
            'https', 'one.example', 443, '93.184.216.34', '/start', 'one.example'
        )
        second = ResolvedPublicURL(
            'https', 'two.example', 443, '8.8.8.8', '/next', 'two.example'
        )
        mock_resolve.side_effect = [first, second]
        redirect = MagicMock(
            status_code=302,
            headers={'Location': 'https://two.example/next'},
            url='https://one.example/start',
        )
        final = MagicMock(status_code=200, headers={}, url='https://two.example/next')
        mock_get.side_effect = [redirect, final]

        result = fetch_public_url('https://one.example/start')

        self.assertIs(result, final)
        self.assertEqual([call.args[0].ip for call in mock_get.call_args_list], [
            '93.184.216.34',
            '8.8.8.8',
        ])
        self.assertEqual(mock_resolve.call_count, 2)

    @patch('utils.url_safety._get_from_public_target')
    @patch('utils.url_safety.resolve_public_url')
    def test_unsafe_redirect_is_blocked_before_second_fetch(self, mock_resolve, mock_get):
        first = ResolvedPublicURL(
            'https', 'one.example', 443, '93.184.216.34', '/start', 'one.example'
        )
        mock_resolve.side_effect = [first, UnsafeURLError('private')]
        mock_get.return_value = MagicMock(
            status_code=302,
            headers={'Location': 'http://127.0.0.1/admin'},
            url='https://one.example/start',
        )

        with self.assertRaises(UnsafeURLError):
            fetch_public_url('https://one.example/start')

        mock_get.assert_called_once()

    def test_declared_oversized_response_is_rejected_without_body_read(self):
        raw = MagicMock()
        raw.getheader.return_value = '101'

        with self.assertRaises(PublicFetchTooLarge):
            _read_bounded_body(raw, 100)

        raw.read.assert_not_called()

    def test_streaming_oversized_response_is_rejected(self):
        raw = MagicMock()
        raw.getheader.return_value = None
        raw.read.side_effect = [b'a' * 80, b'b' * 21]

        with self.assertRaises(PublicFetchTooLarge):
            _read_bounded_body(raw, 100)

    def test_malformed_content_length_is_rejected(self):
        raw = MagicMock()
        raw.getheader.return_value = 'not-a-number'

        with self.assertRaises(requests.RequestException):
            _read_bounded_body(raw, 100)


if __name__ == '__main__':
    unittest.main()
