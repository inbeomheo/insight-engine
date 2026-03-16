"""웹훅 SSRF 방어 강화 테스트 — _validate_webhook_url, _is_dangerous_ip"""
import unittest
from unittest.mock import patch
import ipaddress

from services.platform.webhook_service import _validate_webhook_url, _is_dangerous_ip


class TestIsDangerousIp(unittest.TestCase):
    """_is_dangerous_ip 함수 테스트"""

    def test_loopback_v4(self):
        self.assertTrue(_is_dangerous_ip(ipaddress.ip_address('127.0.0.1')))

    def test_loopback_v6(self):
        self.assertTrue(_is_dangerous_ip(ipaddress.ip_address('::1')))

    def test_private_10(self):
        self.assertTrue(_is_dangerous_ip(ipaddress.ip_address('10.0.0.1')))

    def test_private_192(self):
        self.assertTrue(_is_dangerous_ip(ipaddress.ip_address('192.168.1.1')))

    def test_link_local(self):
        self.assertTrue(_is_dangerous_ip(ipaddress.ip_address('169.254.169.254')))

    def test_ipv4_mapped_v6_private(self):
        """::ffff:127.0.0.1 같은 IPv4-mapped IPv6 차단"""
        self.assertTrue(_is_dangerous_ip(ipaddress.ip_address('::ffff:127.0.0.1')))

    def test_ipv4_mapped_v6_private_192(self):
        self.assertTrue(_is_dangerous_ip(ipaddress.ip_address('::ffff:192.168.0.1')))

    def test_public_ip_safe(self):
        self.assertFalse(_is_dangerous_ip(ipaddress.ip_address('8.8.8.8')))

    def test_public_v6_safe(self):
        self.assertFalse(_is_dangerous_ip(ipaddress.ip_address('2001:4860:4860::8888')))


class TestValidateWebhookUrl(unittest.TestCase):
    """_validate_webhook_url SSRF 방어 테스트"""

    def test_public_https_allowed(self):
        self.assertTrue(_validate_webhook_url('https://hooks.slack.com/services/T123'))

    def test_http_allowed(self):
        self.assertTrue(_validate_webhook_url('http://example.com/hook'))

    def test_ftp_blocked(self):
        self.assertFalse(_validate_webhook_url('ftp://example.com/file'))

    def test_empty_url(self):
        self.assertFalse(_validate_webhook_url(''))

    def test_no_scheme(self):
        self.assertFalse(_validate_webhook_url('example.com/hook'))

    def test_localhost_blocked(self):
        self.assertFalse(_validate_webhook_url('http://localhost:8080/hook'))

    def test_127_blocked(self):
        self.assertFalse(_validate_webhook_url('http://127.0.0.1/hook'))

    def test_private_10_blocked(self):
        self.assertFalse(_validate_webhook_url('http://10.0.0.1/hook'))

    def test_private_192_blocked(self):
        self.assertFalse(_validate_webhook_url('http://192.168.1.1/hook'))

    def test_metadata_google_blocked(self):
        """GCP 메타데이터 엔드포인트 차단"""
        self.assertFalse(_validate_webhook_url('http://metadata.google.internal/computeMetadata/v1/'))

    def test_aws_metadata_ip_blocked(self):
        """AWS 메타데이터 엔드포인트(169.254.169.254) 차단"""
        self.assertFalse(_validate_webhook_url('http://169.254.169.254/latest/meta-data/'))

    def test_ipv6_loopback_blocked(self):
        """IPv6 루프백 [::1] 차단"""
        self.assertFalse(_validate_webhook_url('http://[::1]/hook'))

    def test_ipv4_mapped_v6_blocked(self):
        """IPv4-mapped IPv6 ::ffff:127.0.0.1 차단"""
        self.assertFalse(_validate_webhook_url('http://[::ffff:127.0.0.1]/hook'))

    @patch('socket.getaddrinfo')
    def test_dns_resolving_to_private_blocked(self, mock_getaddrinfo):
        """도메인이 사설 IP로 해석되면 차단 (DNS 리바인딩 방어)"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('127.0.0.1', 80))
        ]
        self.assertFalse(_validate_webhook_url('https://evil.example.com/hook'))

    @patch('socket.getaddrinfo')
    def test_dns_resolving_to_public_allowed(self, mock_getaddrinfo):
        """도메인이 공개 IP로 해석되면 허용"""
        mock_getaddrinfo.return_value = [
            (2, 1, 6, '', ('93.184.216.34', 443))
        ]
        self.assertTrue(_validate_webhook_url('https://example.com/hook'))

    @patch('socket.getaddrinfo')
    def test_dns_failure_blocked(self, mock_getaddrinfo):
        """DNS 해석 실패 (존재하지 않는 도메인)은 차단"""
        import socket
        mock_getaddrinfo.side_effect = socket.gaierror('Name not found')
        self.assertFalse(_validate_webhook_url('https://nonexistent.invalid/hook'))

    def test_zero_ip_blocked(self):
        """0.0.0.0 차단"""
        self.assertFalse(_validate_webhook_url('http://0.0.0.0/hook'))


if __name__ == '__main__':
    unittest.main()
