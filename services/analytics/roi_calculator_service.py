"""
콘텐츠 ROI 계산기 서비스 (F6-08)
생성 비용 대비 트래픽 가치 ROI 계산
"""
from typing import Any

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('ROICalculatorService')

# 트래픽 가치 기준값 (USD/방문자) — 업계 평균
DEFAULT_VALUE_PER_VISITOR_USD = 0.05
# CPC 기준 유기 클릭 가치 (USD/클릭)
DEFAULT_CPC_USD = 1.5


class ROICalculatorService:
    """콘텐츠 ROI (투자 대비 수익률) 계산"""

    def __init__(self,
                 value_per_visitor: float = DEFAULT_VALUE_PER_VISITOR_USD,
                 cpc_usd: float = DEFAULT_CPC_USD):
        self.value_per_visitor = value_per_visitor
        self.cpc_usd = cpc_usd

    def calculate_roi(
        self,
        generation_cost_usd: float,
        views: int,
        clicks: int = 0,
        conversions: int = 0,
        revenue_per_conversion_usd: float = 0.0,
    ) -> dict[str, Any]:
        """
        ROI 계산

        Args:
            generation_cost_usd: 콘텐츠 생성 API 비용 (USD)
            views: 페이지뷰 수
            clicks: 유기 검색 클릭 수 (GSC 기준)
            conversions: 전환 수 (구매/가입 등)
            revenue_per_conversion_usd: 전환당 수익 (USD)

        Returns:
            dict: 비용, 가치, ROI%, 손익분기점 등
        """
        # 트래픽 가치 = 방문자 × 방문자당 가치
        traffic_value = views * self.value_per_visitor
        # SEO 클릭 가치 = 유기 클릭 × CPC
        seo_value = clicks * self.cpc_usd
        # 전환 수익
        conversion_revenue = conversions * revenue_per_conversion_usd
        # 총 가치
        total_value = traffic_value + seo_value + conversion_revenue

        roi_pct = (
            (total_value - generation_cost_usd) / generation_cost_usd * 100
            if generation_cost_usd > 0 else 0.0
        )
        # 손익분기 방문자 수
        breakeven_views = (
            int(generation_cost_usd / self.value_per_visitor)
            if self.value_per_visitor > 0 else 0
        )

        return {
            'generation_cost_usd': round(generation_cost_usd, 4),
            'traffic_value_usd': round(traffic_value, 4),
            'seo_value_usd': round(seo_value, 4),
            'conversion_revenue_usd': round(conversion_revenue, 4),
            'total_value_usd': round(total_value, 4),
            'roi_pct': round(roi_pct, 1),
            'net_gain_usd': round(total_value - generation_cost_usd, 4),
            'breakeven_views': breakeven_views,
        }

    def batch_roi(self, contents: list[dict]) -> list[dict]:
        """
        여러 콘텐츠 ROI 일괄 계산

        각 항목은 calculate_roi와 동일한 키를 포함해야 함 + content_id
        """
        results = []
        for item in contents:
            content_id = item.get('content_id', '')
            roi = self.calculate_roi(
                generation_cost_usd=item.get('generation_cost_usd', 0),
                views=item.get('views', 0),
                clicks=item.get('clicks', 0),
                conversions=item.get('conversions', 0),
                revenue_per_conversion_usd=item.get('revenue_per_conversion_usd', 0),
            )
            roi['content_id'] = content_id
            results.append(roi)
        # ROI 내림차순 정렬
        results.sort(key=lambda x: x['roi_pct'], reverse=True)
        return results
