"""
Google Analytics 4 연동 서비스 (F6-03)
GA4 Data API를 통해 트래픽 / 이벤트 데이터 조회
"""
import os
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('GAService')

GA4_PROPERTY_ID: str = os.getenv('GA4_PROPERTY_ID', '')
GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')


class GAService:
    """Google Analytics 4 Data API 클라이언트"""

    def __init__(self, property_id: str | None = None):
        self.property_id = property_id or GA4_PROPERTY_ID
        self._client = None

    def _get_client(self) -> Any:
        """google-analytics-data 클라이언트 초기화 (지연 로딩)"""
        if self._client is None:
            try:
                from google.analytics.data_v1beta import BetaAnalyticsDataClient
                self._client = BetaAnalyticsDataClient()
            except ImportError:
                logger.warning('google-analytics-data 패키지 미설치. pip install google-analytics-data')
                return None
        return self._client

    def is_enabled(self) -> bool:
        """GA4 연동 사용 가능 여부"""
        return bool(self.property_id and GOOGLE_APPLICATION_CREDENTIALS)

    def get_page_views(self, days: int = 30) -> dict[str, Any]:
        """최근 N일 페이지뷰 조회"""
        if not self.is_enabled():
            return {'enabled': False, 'reason': 'GA4_PROPERTY_ID 또는 GOOGLE_APPLICATION_CREDENTIALS 미설정'}

        client = self._get_client()
        if client is None:
            return {'enabled': False, 'reason': 'google-analytics-data 패키지 필요'}

        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest, DateRange, Dimension, Metric
            )
            request = RunReportRequest(
                property=f'properties/{self.property_id}',
                date_ranges=[DateRange(start_date=f'{days}daysAgo', end_date='today')],
                dimensions=[Dimension(name='pagePath')],
                metrics=[Metric(name='screenPageViews')],
            )
            response = client.run_report(request)
            rows = [
                {
                    'page': row.dimension_values[0].value,
                    'views': int(row.metric_values[0].value),
                }
                for row in response.rows
            ]
            return {'enabled': True, 'days': days, 'rows': rows}
        except Exception as e:
            logger.error(f'GA4 조회 실패: {e}')
            return {'enabled': True, 'error': str(e)}

    def get_event_counts(self, days: int = 30) -> dict[str, Any]:
        """최근 N일 이벤트별 발생 수"""
        if not self.is_enabled():
            return {'enabled': False}

        client = self._get_client()
        if client is None:
            return {'enabled': False}

        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest, DateRange, Dimension, Metric
            )
            request = RunReportRequest(
                property=f'properties/{self.property_id}',
                date_ranges=[DateRange(start_date=f'{days}daysAgo', end_date='today')],
                dimensions=[Dimension(name='eventName')],
                metrics=[Metric(name='eventCount')],
            )
            response = client.run_report(request)
            rows = [
                {
                    'event': row.dimension_values[0].value,
                    'count': int(row.metric_values[0].value),
                }
                for row in response.rows
            ]
            return {'enabled': True, 'days': days, 'rows': rows}
        except Exception as e:
            logger.error(f'GA4 이벤트 조회 실패: {e}')
            return {'enabled': True, 'error': str(e)}
