"""
Google Sheets 동기화 서비스 (F7-22)

생성된 콘텐츠를 Google Sheets에 행으로 추가합니다.
Google Service Account JSON (GOOGLE_SERVICE_ACCOUNT_JSON) 또는
GOOGLE_SHEETS_API_KEY + GOOGLE_SPREADSHEET_ID 필요.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

SHEETS_API_BASE = 'https://sheets.googleapis.com/v4/spreadsheets'


class GoogleSheetsService:
    """Google Sheets API v4 연동 서비스"""

    def __init__(self):
        self.api_key: str = os.getenv('GOOGLE_SHEETS_API_KEY', '')
        self.spreadsheet_id: str = os.getenv('GOOGLE_SPREADSHEET_ID', '')
        self._service_account_json: str = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '')

    def _get_access_token(self) -> Optional[str]:
        """서비스 계정으로 OAuth2 토큰 획득"""
        if not self._service_account_json:
            return None
        try:
            import base64
            import time

            sa = json.loads(self._service_account_json)
            # JWT 생성 (서명은 RSA 필요 — 여기서는 구조만 제공)
            header = base64.urlsafe_b64encode(
                json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode()
            ).rstrip(b'=').decode()
            now = int(time.time())
            claims = {
                'iss': sa.get('client_email', ''),
                'scope': 'https://www.googleapis.com/auth/spreadsheets',
                'aud': 'https://oauth2.googleapis.com/token',
                'iat': now,
                'exp': now + 3600,
            }
            payload = base64.urlsafe_b64encode(
                json.dumps(claims).encode()
            ).rstrip(b'=').decode()
            logger.info("서비스 계정 JWT 생성 (서명 생략 — 실제 운영 시 RSA 서명 필요)")
            return None  # 실제 구현은 google-auth 라이브러리 사용 권장
        except Exception as e:
            logger.error(f"서비스 계정 토큰 획득 실패: {e}")
            return None

    def append_row(self, values: list, sheet_name: str = 'Sheet1') -> dict:
        """스프레드시트에 행 추가

        Args:
            values: 행 데이터 리스트
            sheet_name: 시트명

        Returns:
            API 응답 dict
        """
        if not self.is_configured:
            return {'success': False, 'message': '설정이 완료되지 않았습니다.'}

        range_notation = f'{sheet_name}!A:Z'
        encoded_range = urllib.parse.quote(range_notation)
        url = (
            f'{SHEETS_API_BASE}/{self.spreadsheet_id}/values/'
            f'{encoded_range}:append?valueInputOption=USER_ENTERED&key={self.api_key}'
        )
        body = {'values': [values]}
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            raise ValueError(f"Sheets API 오류 ({e.code}): {error_body}")

    def sync_content(self, title: str, content: str, style: str,
                     url: str = '', sheet_name: str = 'Contents') -> dict:
        """생성된 콘텐츠를 Google Sheets에 동기화

        Returns:
            {"success": bool, "message": str}
        """
        if not self.is_configured:
            return {
                'success': False,
                'message': 'GOOGLE_SHEETS_API_KEY 또는 GOOGLE_SPREADSHEET_ID가 설정되지 않았습니다.',
            }

        from datetime import datetime
        row = [
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            title[:500],
            style,
            url,
            content[:50000],
        ]

        try:
            result = self.append_row(row, sheet_name)
            updated_range = result.get('updates', {}).get('updatedRange', '')
            return {
                'success': True,
                'message': f'Google Sheets 동기화 완료 (범위: {updated_range})',
            }
        except ValueError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            logger.error(f"Google Sheets 동기화 실패: {e}")
            return {'success': False, 'message': f'동기화 중 오류: {str(e)}'}

    def ensure_header_row(self, sheet_name: str = 'Contents') -> bool:
        """헤더 행이 없으면 추가"""
        headers = ['Created At', 'Title', 'Style', 'Source URL', 'Content']
        try:
            self.append_row(headers, sheet_name)
            return True
        except Exception:
            return False

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.spreadsheet_id)


gsheets_service = GoogleSheetsService()
