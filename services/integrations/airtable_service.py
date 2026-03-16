"""
Airtable 동기화 서비스 (F7-21)

생성된 콘텐츠를 Airtable 베이스에 동기화합니다.
AIRTABLE_API_KEY, AIRTABLE_BASE_ID 환경변수 필요.
"""
import json
import logging
import os
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

AIRTABLE_API_BASE = 'https://api.airtable.com/v0'


class AirtableService:
    """Airtable REST API 연동 서비스"""

    def __init__(self):
        self.api_key: str = os.getenv('AIRTABLE_API_KEY', '')
        self.base_id: str = os.getenv('AIRTABLE_BASE_ID', '')

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def _request(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        url = f'{AIRTABLE_API_BASE}/{self.base_id}/{path}'
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            raise ValueError(f"Airtable API 오류 ({e.code}): {error_body}")

    def create_record(self, table_name: str, fields: dict) -> dict:
        """테이블에 레코드 생성

        Args:
            table_name: Airtable 테이블명 (URL 인코딩 필요)
            fields: 필드 데이터 dict

        Returns:
            생성된 레코드 dict
        """
        import urllib.parse
        encoded_table = urllib.parse.quote(table_name, safe='')
        payload = {'fields': fields}
        result = self._request('POST', encoded_table, payload)
        logger.info(f"Airtable 레코드 생성: {result.get('id')} ({table_name})")
        return result

    def update_record(self, table_name: str, record_id: str, fields: dict) -> dict:
        """레코드 업데이트 (PATCH)"""
        import urllib.parse
        encoded_table = urllib.parse.quote(table_name, safe='')
        result = self._request('PATCH', f'{encoded_table}/{record_id}', {'fields': fields})
        return result

    def list_records(self, table_name: str, max_records: int = 100) -> list:
        """레코드 목록 조회"""
        import urllib.parse
        encoded_table = urllib.parse.quote(table_name, safe='')
        url = f'{AIRTABLE_API_BASE}/{self.base_id}/{encoded_table}?maxRecords={max_records}'
        req = urllib.request.Request(url, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                return data.get('records', [])
        except Exception as e:
            logger.error(f"Airtable 레코드 조회 실패: {e}")
            return []

    def sync_content(self, title: str, content: str, style: str,
                     url: str = '', table_name: str = 'Contents') -> dict:
        """생성된 콘텐츠를 Airtable에 동기화

        Returns:
            {"success": bool, "record_id": str | None, "message": str}
        """
        if not self.is_configured:
            return {
                'success': False,
                'record_id': None,
                'message': 'AIRTABLE_API_KEY 또는 AIRTABLE_BASE_ID가 설정되지 않았습니다.',
            }

        from datetime import datetime, timezone
        fields = {
            'Title': title[:255],
            'Style': style,
            'Source URL': url,
            'Content': content[:100000],  # Airtable 필드 최대 길이
            'Created At': datetime.now(timezone.utc).isoformat(),
            'Status': 'Generated',
        }

        try:
            record = self.create_record(table_name, fields)
            return {
                'success': True,
                'record_id': record.get('id'),
                'message': f"Airtable 동기화 완료 (레코드 ID: {record.get('id')})",
            }
        except ValueError as e:
            return {'success': False, 'record_id': None, 'message': str(e)}
        except Exception as e:
            logger.error(f"Airtable 동기화 실패: {e}")
            return {'success': False, 'record_id': None, 'message': f'동기화 중 오류: {str(e)}'}

    @property
    def is_configured(self) -> bool:
        """Airtable API 키 및 Base ID 설정 여부"""
        return bool(self.api_key and self.base_id)


airtable_service = AirtableService()
