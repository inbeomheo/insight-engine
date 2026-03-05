"""
사용 리포트 이메일 서비스 (F4-23)
주간/월간 사용량 리포트 HTML 생성
"""
from datetime import datetime, timezone
from services.logging_config import ServiceLogger

logger = ServiceLogger('ReportEmailService')


class ReportEmailService:
    """사용량 리포트 이메일 생성"""

    def generate_report(
        self,
        user_id: str,
        period: str,
        stats: dict,
    ) -> dict:
        """리포트 HTML 생성

        Args:
            user_id: 사용자 ID
            period: 'weekly' 또는 'monthly'
            stats: {total_generations, total_tokens, top_styles, ...}
        """
        if period not in ('weekly', 'monthly'):
            return {'error': "period는 'weekly' 또는 'monthly'만 허용됩니다."}

        period_label = '주간' if period == 'weekly' else '월간'
        total = stats.get('total_generations', 0)
        tokens = stats.get('total_tokens', 0)
        top_styles = stats.get('top_styles', [])

        # 스타일 목록 HTML
        style_items = ''.join(
            f'<li>{s["name"]}: {s["count"]}회</li>' for s in top_styles[:5]
        )

        html = f"""
<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto;">
  <h2>Insight Engine {period_label} 리포트</h2>
  <p>안녕하세요! 지난 {period_label} 사용 현황입니다.</p>
  <table style="width: 100%; border-collapse: collapse;">
    <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">총 생성 횟수</td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;"><b>{total}</b>회</td></tr>
    <tr><td style="padding: 8px; border-bottom: 1px solid #eee;">총 토큰 사용량</td>
        <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;"><b>{tokens:,}</b></td></tr>
  </table>
  {'<h3>인기 스타일 TOP 5</h3><ul>' + style_items + '</ul>' if style_items else ''}
  <p style="color: #666; font-size: 12px;">이 이메일은 자동 발송됩니다.</p>
</div>
"""

        report = {
            'user_id': user_id,
            'period': period,
            'subject': f'[Insight Engine] {period_label} 사용 리포트',
            'html': html.strip(),
            'generated_at': datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"리포트 생성: {user_id[:8]}... ({period})")
        return report


report_email_service = ReportEmailService()
