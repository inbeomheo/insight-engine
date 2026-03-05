"""
이메일 알림 서비스 (F6-21)
SMTP 또는 SendGrid를 통해 이메일 발송
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from services.logging_config import ServiceLogger

logger = ServiceLogger('EmailService')

# SMTP 설정
SMTP_HOST: str = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT: int = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER: str = os.getenv('SMTP_USER', '')
SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')
SMTP_FROM: str = os.getenv('SMTP_FROM', SMTP_USER)

# SendGrid 설정
SENDGRID_API_KEY: str = os.getenv('SENDGRID_API_KEY', '')


class EmailService:
    """이메일 발송 서비스 (SMTP / SendGrid 지원)"""

    def __init__(self):
        self._use_sendgrid = bool(SENDGRID_API_KEY)
        self._use_smtp = bool(SMTP_USER and SMTP_PASSWORD)

    def is_enabled(self) -> bool:
        return self._use_sendgrid or self._use_smtp

    def send(self, to: str | list[str], subject: str,
             body_text: str, body_html: str = '') -> dict[str, Any]:
        """이메일 발송 (SendGrid 우선, 없으면 SMTP)"""
        recipients = [to] if isinstance(to, str) else to
        if not recipients:
            return {'ok': False, 'reason': '수신자 없음'}

        if self._use_sendgrid:
            return self._send_sendgrid(recipients, subject, body_text, body_html)
        if self._use_smtp:
            return self._send_smtp(recipients, subject, body_text, body_html)
        return {'ok': False, 'reason': 'SMTP 또는 SendGrid 설정 필요'}

    def _send_smtp(self, recipients: list[str], subject: str,
                   body_text: str, body_html: str) -> dict[str, Any]:
        """SMTP로 이메일 발송"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = SMTP_FROM
            msg['To'] = ', '.join(recipients)
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            if body_html:
                msg.attach(MIMEText(body_html, 'html', 'utf-8'))

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, recipients, msg.as_string())

            logger.info(f'SMTP 발송 완료: {recipients}')
            return {'ok': True, 'method': 'smtp', 'recipients': recipients}
        except Exception as e:
            logger.error(f'SMTP 발송 실패: {e}')
            return {'ok': False, 'method': 'smtp', 'error': str(e)}

    def _send_sendgrid(self, recipients: list[str], subject: str,
                       body_text: str, body_html: str) -> dict[str, Any]:
        """SendGrid API로 이메일 발송"""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Content, To

            to_list = [To(r) for r in recipients]
            mail = Mail(
                from_email=SMTP_FROM or 'noreply@insight-engine.io',
                to_emails=to_list,
                subject=subject,
                plain_text_content=body_text,
            )
            if body_html:
                mail.content = [
                    Content('text/plain', body_text),
                    Content('text/html', body_html),
                ]

            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(mail)
            logger.info(f'SendGrid 발송 완료: {recipients}, status={response.status_code}')
            return {'ok': True, 'method': 'sendgrid', 'status': response.status_code}
        except ImportError:
            logger.warning('sendgrid 패키지 미설치 — SMTP로 폴백')
            return self._send_smtp(recipients, subject, body_text, body_html)
        except Exception as e:
            logger.error(f'SendGrid 발송 실패: {e}')
            return {'ok': False, 'method': 'sendgrid', 'error': str(e)}

    def send_weekly_digest(self, to: str | list[str], stats: dict) -> dict[str, Any]:
        """주간 다이제스트 이메일 발송"""
        subject = f'[Insight Engine] 주간 리포트 — 생성 {stats.get("total", 0)}건'
        body_text = (
            f'안녕하세요,\n\n'
            f'이번 주 Insight Engine 사용 현황입니다.\n\n'
            f'총 생성: {stats.get("total", 0)}건\n'
            f'성공률: {stats.get("success_rate", 0)}%\n'
            f'총 비용: ${stats.get("total_cost_usd", 0):.4f}\n\n'
            f'자세한 내용은 대시보드를 확인하세요.'
        )
        return self.send(to, subject, body_text)
