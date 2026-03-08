"""
AI 요약 뉴스레터 자동 발송 서비스 (F10-24)
정기 구독 콘텐츠를 자동으로 요약하여 이메일로 발송
"""
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
SMTP_HOST = os.getenv('SMTP_HOST', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')
NEWSLETTER_FROM_EMAIL = os.getenv('NEWSLETTER_FROM_EMAIL', 'newsletter@insight-engine.com')
NEWSLETTER_FROM_NAME = os.getenv('NEWSLETTER_FROM_NAME', 'Insight Engine')


@dataclass
class NewsletterIssue:
    """뉴스레터 이슈"""
    issue_id: str
    subject: str
    html_body: str
    text_body: str
    recipients: List[str]
    created_at: float = field(default_factory=time.time)
    sent_count: int = 0
    failed_count: int = 0


def _send_with_sendgrid(issue: NewsletterIssue) -> Dict[str, int]:
    """SendGrid API로 이메일 발송"""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx 필요: pip install httpx")

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "personalizations": [
            {"to": [{"email": email}]} for email in issue.recipients
        ],
        "from": {"email": NEWSLETTER_FROM_EMAIL, "name": NEWSLETTER_FROM_NAME},
        "subject": issue.subject,
        "content": [
            {"type": "text/plain", "value": issue.text_body},
            {"type": "text/html", "value": issue.html_body},
        ],
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers=headers,
        )

    if resp.status_code not in (200, 202):
        raise RuntimeError(f"SendGrid 오류: {resp.status_code} {resp.text[:200]}")

    return {'sent': len(issue.recipients), 'failed': 0}


def _send_with_smtp(issue: NewsletterIssue) -> Dict[str, int]:
    """SMTP로 이메일 발송"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    sent = 0
    failed = 0

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)

        for recipient in issue.recipients:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = issue.subject
                msg['From'] = f"{NEWSLETTER_FROM_NAME} <{NEWSLETTER_FROM_EMAIL}>"
                msg['To'] = recipient
                msg.attach(MIMEText(issue.text_body, 'plain', 'utf-8'))
                msg.attach(MIMEText(issue.html_body, 'html', 'utf-8'))
                smtp.sendmail(NEWSLETTER_FROM_EMAIL, recipient, msg.as_string())
                sent += 1
            except Exception as e:
                logger.warning("SMTP 발송 실패: %s — %s", recipient, e)
                failed += 1

    return {'sent': sent, 'failed': failed}


class AutoNewsletterService:
    """
    AI 뉴스레터 자동 발송 서비스

    기능:
    1. RSS/YouTube 채널에서 최신 콘텐츠 수집
    2. AI로 요약 생성
    3. 뉴스레터 HTML 조립
    4. 구독자 이메일 발송
    """

    def generate_newsletter(
        self,
        content_items: List[Dict[str, str]],
        newsletter_title: str = 'Insight Engine 주간 뉴스레터',
        language: str = 'ko',
        model: Optional[str] = None,
    ) -> NewsletterIssue:
        """
        콘텐츠 아이템 목록에서 뉴스레터 생성

        Args:
            content_items: [{'title': str, 'content': str, 'url': str}, ...]
            newsletter_title: 뉴스레터 제목

        Returns:
            NewsletterIssue
        """
        from services.ai_service import call_litellm

        issue_id = str(int(time.time()))
        summaries = []

        for item in content_items[:5]:  # 최대 5개 아이템
            try:
                summary = self._summarize_item(item, language=language, model=model)
                summaries.append({
                    'title': item.get('title', ''),
                    'summary': summary,
                    'url': item.get('url', ''),
                })
            except Exception as e:
                logger.warning("아이템 요약 실패: %s", e)

        html_body = self._build_html(newsletter_title, summaries)
        text_body = self._build_text(newsletter_title, summaries)

        from datetime import datetime
        subject = f"{newsletter_title} ({datetime.now().strftime('%Y-%m-%d')})"

        return NewsletterIssue(
            issue_id=issue_id,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            recipients=[],  # send()에서 주입
        )

    def send(self, issue: NewsletterIssue, recipients: List[str]) -> Dict[str, int]:
        """뉴스레터 발송"""
        issue.recipients = recipients

        if not recipients:
            return {'sent': 0, 'failed': 0, 'error': '수신자 없음'}

        # SendGrid 우선
        if SENDGRID_API_KEY:
            try:
                result = _send_with_sendgrid(issue)
                issue.sent_count = result['sent']
                issue.failed_count = result['failed']
                logger.info("SendGrid 발송 완료: %d명", result['sent'])
                return result
            except Exception as e:
                logger.warning("SendGrid 실패, SMTP 폴백: %s", e)

        # SMTP 폴백
        if SMTP_HOST and SMTP_USER:
            result = _send_with_smtp(issue)
            issue.sent_count = result['sent']
            issue.failed_count = result['failed']
            logger.info("SMTP 발송 완료: %d명", result['sent'])
            return result

        raise RuntimeError(
            "이메일 발송 설정 없음. SENDGRID_API_KEY 또는 SMTP_HOST/USER/PASS 설정 필요."
        )

    def _summarize_item(
        self,
        item: Dict[str, str],
        language: str = 'ko',
        model: Optional[str] = None,
    ) -> str:
        """단일 콘텐츠 아이템 AI 요약"""
        from services.ai_service import call_litellm

        lang_prompt = {'en': 'in English', 'ja': '日本語で'}.get(language, '한국어로')
        messages = [
            {"role": "system", "content": f"콘텐츠를 3-4문장으로 핵심만 {lang_prompt} 요약하세요."},
            {"role": "user", "content": item.get('content', '')[:3000]},
        ]
        resp = call_litellm(
            messages,
            model=model or os.getenv('NEWSLETTER_MODEL', 'gemini/gemini-2.5-flash-lite-preview-09-2025'),
            max_tokens=500,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()

    def _build_html(self, title: str, summaries: List[Dict]) -> str:
        items_html = ''
        for item in summaries:
            url_html = f'<a href="{item["url"]}">원문 보기 →</a>' if item.get('url') else ''
            items_html += f"""
            <div style="margin-bottom:24px; padding-bottom:24px; border-bottom:1px solid #eee;">
                <h3 style="margin:0 0 8px; color:#1a1a1a;">{item['title']}</h3>
                <p style="margin:0 0 8px; color:#444; line-height:1.6;">{item['summary']}</p>
                {url_html}
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>{title}</title></head>
        <body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333;">
            <h1 style="color:#6366f1;border-bottom:2px solid #6366f1;padding-bottom:12px;">{title}</h1>
            {items_html}
            <footer style="margin-top:40px;padding-top:20px;border-top:1px solid #eee;font-size:12px;color:#888;">
                Insight Engine 뉴스레터 | 구독 취소는 회신 이메일로 문의하세요.
            </footer>
        </body>
        </html>
        """

    def _build_text(self, title: str, summaries: List[Dict]) -> str:
        lines = [title, '=' * len(title), '']
        for item in summaries:
            lines.append(f"■ {item['title']}")
            lines.append(item['summary'])
            if item.get('url'):
                lines.append(f"원문: {item['url']}")
            lines.append('')
        lines.append('---')
        lines.append('Insight Engine 뉴스레터')
        return '\n'.join(lines)
