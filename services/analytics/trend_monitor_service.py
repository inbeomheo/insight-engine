"""
트렌드 키워드 모니터 서비스 (F6-07)
Google Trends API (pytrends) 또는 직접 수집으로 키워드 추세 추적
"""
import os
from datetime import datetime, timezone
from typing import Any

from services.logging_config import ServiceLogger

logger = ServiceLogger('TrendMonitorService')

TRENDS_GEO: str = os.getenv('TRENDS_GEO', 'KR')  # 기본 한국


class TrendMonitorService:
    """키워드 트렌드 모니터링"""

    def __init__(self):
        # 추적 키워드 목록
        self._keywords: list[str] = []
        # 수집된 트렌드 데이터 캐시: keyword → [{date, value}]
        self._cache: dict[str, list[dict]] = {}
        self._cache_updated: str | None = None

    def add_keyword(self, keyword: str) -> None:
        """추적 키워드 추가"""
        if keyword not in self._keywords:
            self._keywords.append(keyword)
            logger.info(f'트렌드 키워드 추가: {keyword}')

    def remove_keyword(self, keyword: str) -> None:
        """추적 키워드 제거"""
        if keyword in self._keywords:
            self._keywords.remove(keyword)

    def get_keywords(self) -> list[str]:
        """현재 추적 중인 키워드 목록 반환"""
        return list(self._keywords)

    def fetch_trends(self, keywords: list[str] | None = None,
                     timeframe: str = 'today 3-m') -> dict[str, Any]:
        """Google Trends 데이터 수집 (pytrends 라이브러리 필요)"""
        targets = keywords or self._keywords
        if not targets:
            return {'error': '추적 키워드 없음'}

        try:
            from pytrends.request import TrendReq
            pt = TrendReq(hl='ko-KR', geo=TRENDS_GEO)
            # pytrends는 한 번에 최대 5개 키워드
            result: dict[str, list[dict]] = {}
            for i in range(0, len(targets), 5):
                batch = targets[i:i + 5]
                pt.build_payload(batch, timeframe=timeframe)
                df = pt.interest_over_time()
                if df.empty:
                    continue
                for kw in batch:
                    if kw in df.columns:
                        series = df[kw].dropna()
                        result[kw] = [
                            {'date': str(idx.date()), 'value': int(val)}
                            for idx, val in series.items()
                        ]

            self._cache.update(result)
            self._cache_updated = datetime.now(timezone.utc).isoformat()
            return {
                'geo': TRENDS_GEO,
                'timeframe': timeframe,
                'updated_at': self._cache_updated,
                'data': result,
            }
        except ImportError:
            logger.warning('pytrends 패키지 미설치. pip install pytrends')
            return {'error': 'pytrends 패키지 필요', 'stub': True, 'keywords': targets}
        except Exception as e:
            logger.error(f'Google Trends 조회 실패: {e}')
            return {'error': str(e)}

    def get_cached(self) -> dict[str, Any]:
        """마지막으로 수집된 캐시 반환"""
        return {
            'updated_at': self._cache_updated,
            'data': self._cache,
        }

    def get_rising_keywords(self, keywords: list[str] | None = None) -> dict[str, Any]:
        """급상승 키워드 조회"""
        targets = keywords or self._keywords
        if not targets:
            return {'error': '추적 키워드 없음'}

        try:
            from pytrends.request import TrendReq
            pt = TrendReq(hl='ko-KR', geo=TRENDS_GEO)
            pt.build_payload(targets[:5])
            rising = pt.related_queries()
            result = {
                kw: data.get('rising', None).head(5).to_dict('records')
                if data.get('rising') is not None else []
                for kw, data in rising.items()
            }
            return {'geo': TRENDS_GEO, 'rising': result}
        except ImportError:
            return {'error': 'pytrends 패키지 필요', 'stub': True}
        except Exception as e:
            return {'error': str(e)}
