"""
Telegram 봇 서비스 (F7-04)

Telegram Bot API (webhook 기반)를 통해
URL 전송 시 자동으로 콘텐츠 생성을 요청합니다.
TELEGRAM_BOT_TOKEN 환경변수 필요.
"""
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

YOUTUBE_URL_RE = re.compile(
    r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
)

TELEGRAM_API_BASE = 'https://api.telegram.org/bot'


class TelegramBotService:
    """Telegram Bot API 웹훅 처리 서비스"""

    def __init__(self):
        self.bot_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')

    @property
    def api_url(self) -> str:
        """Telegram Bot API 엔드포인트 URL"""
        return f'{TELEGRAM_API_BASE}{self.bot_token}'

    def handle_update(self, update: dict) -> dict:
        """Telegram Update 처리

        Returns:
            처리 결과 dict
        """
        message = update.get('message') or update.get('channel_post')
        if not message:
            return {'ok': True}

        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id')

        if not chat_id:
            return {'ok': True}

        if text.startswith('/start'):
            return self._handle_start(chat_id)
        if text.startswith('/styles'):
            return self._handle_styles(chat_id)
        if text.startswith('/generate'):
            return self._handle_generate(chat_id, text)
        return self._handle_url_message(chat_id, text)

    def _handle_start(self, chat_id: int) -> dict:
        """/start 명령어 처리"""
        self._send_message(
            chat_id,
            '👋 안녕하세요! Insight Engine 봇입니다.\n\n'
            'YouTube 영상 URL을 전송하면 AI 콘텐츠 생성을 도와드립니다.\n\n'
            '사용법:\n'
            '1. YouTube URL을 이 채팅에 붙여넣기\n'
            '2. 스타일을 선택하면 콘텐츠가 생성됩니다.\n\n'
            '명령어:\n'
            '/generate <URL> — 블로그 SEO 스타일로 생성\n'
            '/styles — 지원 스타일 목록',
        )
        return {'ok': True}

    def _handle_styles(self, chat_id: int) -> dict:
        """/styles 명령어 처리"""
        self._send_message(
            chat_id,
            '📋 지원 콘텐츠 스타일:\n\n'
            '• blog_seo — 블로그 SEO\n'
            '• summary — 요약\n'
            '• tutorial — 튜토리얼\n'
            '• qna — Q&A\n'
            '• sns_post — SNS 포스트\n'
            '• newsletter — 뉴스레터\n\n'
            '사용: /generate <URL> <스타일>',
        )
        return {'ok': True}

    def _handle_generate(self, chat_id: int, text: str) -> dict:
        """/generate 명령어 처리"""
        parts = text.split()
        url = parts[1] if len(parts) > 1 else ''
        style = parts[2] if len(parts) > 2 else 'blog_seo'

        if not YOUTUBE_URL_RE.search(url):
            self._send_message(chat_id, '❌ 유효한 YouTube URL을 입력해주세요.')
            return {'ok': True}

        logger.info(f"Telegram 봇: /generate — {url} (스타일: {style})")
        self._send_message(
            chat_id,
            f'⏳ 콘텐츠 생성 요청을 접수했습니다.\n\n'
            f'URL: {url}\n'
            f'스타일: {style}\n\n'
            f'Insight Engine 서버에서 결과를 확인하세요.',
        )
        return {'ok': True, 'url': url, 'style': style}

    def _handle_url_message(self, chat_id: int, text: str) -> dict:
        """URL이 포함된 일반 메시지 처리"""
        urls = YOUTUBE_URL_RE.findall(text)
        if not urls:
            return {'ok': True}

        youtube_url = urls[0]
        logger.info(f"Telegram 봇: URL 감지 — {youtube_url}")

        keyboard = {
            'inline_keyboard': [
                [
                    {'text': '📝 블로그 SEO', 'callback_data': f'gen:blog_seo:{youtube_url}'},
                    {'text': '📋 요약', 'callback_data': f'gen:summary:{youtube_url}'},
                ],
                [
                    {'text': '📱 SNS 포스트', 'callback_data': f'gen:sns_post:{youtube_url}'},
                    {'text': '📰 뉴스레터', 'callback_data': f'gen:newsletter:{youtube_url}'},
                ],
            ]
        }
        self._send_message(
            chat_id,
            f'🎬 YouTube URL을 감지했습니다!\n`{youtube_url}`\n\n콘텐츠 스타일을 선택하세요:',
            reply_markup=keyboard,
        )
        return {'ok': True}

    def handle_callback_query(self, callback_query: dict) -> dict:
        """인라인 키보드 콜백 처리"""
        data = callback_query.get('data', '')
        chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
        callback_id = callback_query.get('id')

        if data.startswith('gen:'):
            parts = data.split(':', 2)
            if len(parts) == 3:
                _, style, url = parts
                logger.info(f"Telegram 봇: 콜백 생성 — {url} (스타일: {style})")
                self._answer_callback(callback_id, '생성을 요청했습니다!')
                if chat_id:
                    self._send_message(
                        chat_id,
                        f'⏳ `{style}` 스타일로 생성 중입니다...\nInsight Engine 서버에서 결과를 확인하세요.',
                    )
                return {'ok': True, 'url': url, 'style': style}

        return {'ok': True}

    def _send_message(self, chat_id: int, text: str, reply_markup: Optional[dict] = None) -> Optional[dict]:
        """Telegram 메시지 전송"""
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
            return None

        try:
            import urllib.request
            payload: dict = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
            if reply_markup:
                payload['reply_markup'] = reply_markup

            req = urllib.request.Request(
                f'{self.api_url}/sendMessage',
                data=json.dumps(payload).encode(),
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.error(f"Telegram 메시지 전송 실패: {e}")
            return None

    def _answer_callback(self, callback_id: str, text: str) -> None:
        """콜백 쿼리 응답"""
        if not self.bot_token:
            return
        try:
            import urllib.request
            payload = json.dumps({'callback_query_id': callback_id, 'text': text}).encode()
            req = urllib.request.Request(
                f'{self.api_url}/answerCallbackQuery',
                data=payload,
                headers={'Content-Type': 'application/json'},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.error(f"Telegram 콜백 응답 실패: {e}")

    def set_webhook(self, webhook_url: str) -> bool:
        """Telegram 웹훅 URL 등록"""
        if not self.bot_token:
            return False
        try:
            import urllib.request
            payload = json.dumps({'url': webhook_url}).encode()
            req = urllib.request.Request(
                f'{self.api_url}/setWebhook',
                data=payload,
                headers={'Content-Type': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                return result.get('ok', False)
        except Exception as e:
            logger.error(f"Telegram 웹훅 등록 실패: {e}")
            return False

    @property
    def is_configured(self) -> bool:
        """Telegram 봇 토큰 설정 여부"""
        return bool(self.bot_token)


telegram_bot_service = TelegramBotService()
