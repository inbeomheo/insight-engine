"""
Google Search Console 연동 서비스 (F6-04)
GSC API를 통해 검색 순위 / CTR 데이터 조회
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('GSCService')

GSC_SITE_URL: str = os.getenv('GSC_SITE_URL', '')
GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')


class GSCService:
    """Google Search Console Data API 클라이언트"""

    def __init__(self, site_url: str | None = None):
        self.site_url = site_url or GSC_SITE_URL
        self._service = None

    def _get_service(self) -> Any:
        """GSC API 서비스 초기화 (지연 로딩)"""
        if self._service is None:
            try:
                from googleapiclient.discovery import build
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_file(
                    GOOGLE_APPLICATION_CREDENTIALS,
                    scopes=['https://www.googleapis.com/auth/webmasters.readonly'],
                )
                self._service = build('searchconsole', 'v1', credentials=creds)
            except ImportError:
                logger.warning('google-api-python-client 패키지 미설치.')
                return None
            except Exception as e:
                logger.error(f'GSC 서비스 초기화 실패: {e}')
                return None
        return self._service

    def is_enabled(self) -> bool:
        """GSC 연동 가능 여부 (사이트 URL + 인증 정보 확인)"""
        return bool(self.site_url and GOOGLE_APPLICATION_CREDENTIALS)

    def get_search_analytics(self, days: int = 30, row_limit: int = 25) -> dict[str, Any]:
        """최근 N일 검색어별 클릭수/노출/CTR/순위"""
        if not self.is_enabled():
            return {'enabled': False, 'reason': 'GSC_SITE_URL 또는 인증 미설정'}

        service = self._get_service()
        if service is None:
            return {'enabled': False, 'reason': 'google-api-python-client 필요'}

        end_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime('%Y-%m-%d')
        start_date = (datetime.now(timezone.utc) - timedelta(days=days + 3)).strftime('%Y-%m-%d')

        try:
            body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['query'],
                'rowLimit': row_limit,
            }
            response = (
                service.searchanalytics()
                .query(siteUrl=self.site_url, body=body)
                .execute()
            )
            rows = [
                {
                    'query': r['keys'][0],
                    'clicks': r['clicks'],
                    'impressions': r['impressions'],
                    'ctr': round(r['ctr'] * 100, 2),
                    'position': round(r['position'], 1),
                }
                for r in response.get('rows', [])
            ]
            return {'enabled': True, 'start': start_date, 'end': end_date, 'rows': rows}
        except Exception as e:
            logger.error(f'GSC 조회 실패: {e}')
            return {'enabled': True, 'error': str(e)}

    def get_top_pages(self, days: int = 30, row_limit: int = 25) -> dict[str, Any]:
        """페이지별 검색 성과"""
        if not self.is_enabled():
            return {'enabled': False}

        service = self._get_service()
        if service is None:
            return {'enabled': False}

        end_date = (datetime.now(timezone.utc) - timedelta(days=3)).strftime('%Y-%m-%d')
        start_date = (datetime.now(timezone.utc) - timedelta(days=days + 3)).strftime('%Y-%m-%d')

        try:
            body = {
                'startDate': start_date,
                'endDate': end_date,
                'dimensions': ['page'],
                'rowLimit': row_limit,
            }
            response = (
                service.searchanalytics()
                .query(siteUrl=self.site_url, body=body)
                .execute()
            )
            rows = [
                {
                    'page': r['keys'][0],
                    'clicks': r['clicks'],
                    'impressions': r['impressions'],
                    'ctr': round(r['ctr'] * 100, 2),
                    'position': round(r['position'], 1),
                }
                for r in response.get('rows', [])
            ]
            return {'enabled': True, 'rows': rows}
        except Exception as e:
            logger.error(f'GSC 페이지 조회 실패: {e}')
            return {'enabled': True, 'error': str(e)}
