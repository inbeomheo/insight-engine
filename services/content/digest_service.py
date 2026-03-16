"""
주간 다이제스트 자동 생성 서비스 (F6-23)
주간 콘텐츠 요약 다이제스트 생성 및 발송
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from services.core.logging_config import ServiceLogger

logger = logging.getLogger(__name__)

logger = ServiceLogger('DigestService')


def _count_by_key(items: list[dict], key: str) -> dict[str, int]:
    """리스트 내 dict들의 특정 키 값별 빈도를 집계합니다."""
    counts: dict[str, int] = {}
    for item in items:
        val = item.get(key, 'unknown')
        counts[val] = counts.get(val, 0) + 1
    return counts


def _compute_digest(recent: list[dict], cutoff: datetime, period_days: int) -> dict[str, Any]:
    """필터된 생성 기록으로 다이제스트 dict를 구성합니다."""
    total = len(recent)
    success = sum(1 for g in recent if g.get('success', True))
    total_tokens = sum(g.get('tokens', 0) for g in recent)

    style_counts = _count_by_key(recent, 'style')
    model_counts = _count_by_key(recent, 'model')
    top_styles = sorted(style_counts.items(), key=lambda x: -x[1])[:5]

    return {
        'period': f'{cutoff.strftime("%Y-%m-%d")} ~ {datetime.now(timezone.utc).strftime("%Y-%m-%d")}',
        'period_days': period_days,
        'total_generations': total,
        'success_count': success,
        'failure_count': total - success,
        'success_rate': round(success / total * 100, 1) if total else 0.0,
        'total_tokens': total_tokens,
        'top_styles': [{'style': s, 'count': c} for s, c in top_styles],
        'model_usage': [{'model': m, 'count': c} for m, c in sorted(model_counts.items(), key=lambda x: -x[1])],
        'generated_at': datetime.now(timezone.utc).isoformat(),
    }


class DigestService:
    """주간 콘텐츠 다이제스트 생성"""

    def __init__(self):
        self._digest_history: list[dict] = []

    def build_digest(
        self,
        generations: list[dict],
        period_days: int = 7,
    ) -> dict[str, Any]:
        """
        주간 다이제스트 데이터 생성

        Args:
            generations: [{title, style, model, tokens, success, created_at}]
            period_days: 집계 기간 (기본 7일)

        Returns:
            다이제스트 dict
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)
        recent = [
            g for g in generations
            if self._parse_ts(g.get('created_at', '')) >= cutoff
        ]

        digest = _compute_digest(recent, cutoff, period_days)
        self._digest_history.append(digest)
        logger.info(f'주간 다이제스트 생성 완료: {len(recent)}건')
        return digest

    def to_text(self, digest: dict) -> str:
        """다이제스트 → 텍스트 형식"""
        lines = [
            f'=== 주간 Insight Engine 리포트 ({digest["period"]}) ===',
            '',
            f'총 생성: {digest["total_generations"]}건 (성공률 {digest["success_rate"]}%)',
            f'총 토큰: {digest["total_tokens"]:,}',
            '',
            '[ 스타일별 순위 ]',
        ]
        for i, item in enumerate(digest.get('top_styles', []), 1):
            lines.append(f'  {i}. {item["style"]}: {item["count"]}건')
        lines.append('')
        lines.append('[ 모델 사용 ]')
        for item in digest.get('model_usage', []):
            lines.append(f'  - {item["model"]}: {item["count"]}건')
        return '\n'.join(lines)

    def to_html(self, digest: dict) -> str:
        """다이제스트 → HTML 형식"""
        style_rows = ''.join(
            f'<tr><td>{i}</td><td>{item["style"]}</td><td>{item["count"]}</td></tr>'
            for i, item in enumerate(digest.get('top_styles', []), 1)
        )
        return f'''<html><body>
<h2>주간 Insight Engine 리포트</h2>
<p><b>기간:</b> {digest["period"]}</p>
<p><b>총 생성:</b> {digest["total_generations"]}건 (성공률 {digest["success_rate"]}%)</p>
<p><b>총 토큰:</b> {digest["total_tokens"]:,}</p>
<h3>스타일별 순위</h3>
<table border="1" cellpadding="5">
<tr><th>#</th><th>스타일</th><th>건수</th></tr>
{style_rows}
</table>
</body></html>'''

    def get_history(self) -> list[dict]:
        """이전 다이제스트 이력"""
        return list(self._digest_history)

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
