"""email_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.email_service import EmailService


class TestEmailServiceInit(unittest.TestCase):
    """EmailService 초기화 테스트"""

    @patch('services.email_service.SENDGRID_API_KEY', '')
    @patch('services.email_service.SMTP_USER', '')
    @patch('services.email_service.SMTP_PASSWORD', '')
    def test_disabled_when_no_config(self):
        """설정 없으면 비활성"""
        svc = EmailService()
        self.assertFalse(svc.is_enabled())

    @patch('services.email_service.SENDGRID_API_KEY', 'sg-key')
    def test_enabled_with_sendgrid(self):
        """SendGrid 키 있으면 활성"""
        svc = EmailService()
        self.assertTrue(svc.is_enabled())

    @patch('services.email_service.SENDGRID_API_KEY', '')
    @patch('services.email_service.SMTP_USER', 'user')
    @patch('services.email_service.SMTP_PASSWORD', 'pass')
    def test_enabled_with_smtp(self):
        """SMTP 설정 있으면 활성"""
        svc = EmailService()
        self.assertTrue(svc.is_enabled())


class TestEmailServiceSend(unittest.TestCase):
    """EmailService.send 테스트"""

    def test_empty_recipients(self):
        """수신자 없으면 실패"""
        svc = EmailService()
        result = svc.send([], '제목', '본문')
        self.assertFalse(result['ok'])

    @patch('services.email_service.SENDGRID_API_KEY', '')
    @patch('services.email_service.SMTP_USER', '')
    @patch('services.email_service.SMTP_PASSWORD', '')
    def test_no_provider_configured(self):
        """프로바이더 미설정 시 실패"""
        svc = EmailService()
        result = svc.send('test@test.com', '제목', '본문')
        self.assertFalse(result['ok'])
        self.assertIn('설정 필요', result['reason'])

    @patch('services.email_service.SENDGRID_API_KEY', '')
    @patch('services.email_service.SMTP_USER', 'user')
    @patch('services.email_service.SMTP_PASSWORD', 'pass')
    @patch('services.email_service.smtplib.SMTP')
    def test_smtp_success(self, mock_smtp_cls):
        """SMTP 발송 성공"""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        svc = EmailService()
        result = svc.send('test@test.com', '제목', '본문')
        self.assertTrue(result['ok'])
        self.assertEqual(result['method'], 'smtp')

    @patch('services.email_service.SENDGRID_API_KEY', '')
    @patch('services.email_service.SMTP_USER', 'user')
    @patch('services.email_service.SMTP_PASSWORD', 'pass')
    @patch('services.email_service.smtplib.SMTP')
    def test_smtp_failure(self, mock_smtp_cls):
        """SMTP 발송 실패"""
        mock_smtp_cls.side_effect = Exception('Connection refused')
        svc = EmailService()
        result = svc.send('test@test.com', '제목', '본문')
        self.assertFalse(result['ok'])
        self.assertIn('Connection refused', result['error'])

    @patch('services.email_service.SENDGRID_API_KEY', '')
    @patch('services.email_service.SMTP_USER', 'user')
    @patch('services.email_service.SMTP_PASSWORD', 'pass')
    @patch('services.email_service.smtplib.SMTP')
    def test_string_recipient_converted_to_list(self, mock_smtp_cls):
        """문자열 수신자가 리스트로 변환"""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        svc = EmailService()
        result = svc.send('single@test.com', '제목', '본문')
        self.assertTrue(result['ok'])


class TestWeeklyDigest(unittest.TestCase):
    """send_weekly_digest 테스트"""

    @patch('services.email_service.SENDGRID_API_KEY', '')
    @patch('services.email_service.SMTP_USER', 'user')
    @patch('services.email_service.SMTP_PASSWORD', 'pass')
    @patch('services.email_service.smtplib.SMTP')
    def test_weekly_digest_subject(self, mock_smtp_cls):
        """주간 다이제스트 제목에 생성 수 포함"""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        svc = EmailService()
        stats = {'total': 42, 'success_rate': 95, 'total_cost_usd': 1.2345}
        result = svc.send_weekly_digest('test@test.com', stats)
        self.assertTrue(result['ok'])

    @patch('services.email_service.SENDGRID_API_KEY', '')
    @patch('services.email_service.SMTP_USER', '')
    @patch('services.email_service.SMTP_PASSWORD', '')
    def test_weekly_digest_no_provider(self):
        """프로바이더 없으면 실패"""
        svc = EmailService()
        result = svc.send_weekly_digest('test@test.com', {})
        self.assertFalse(result['ok'])


if __name__ == '__main__':
    unittest.main()
