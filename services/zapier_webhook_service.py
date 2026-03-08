"""
Zapier 웹훅 강화 서비스 (F6-22)
기존 WebhookService를 확장 — 이벤트별 웹훅 URL 분리 및 필터링 지원
"""
import threading
from typing import Any

from services.webhook_service import WebhookService, _validate_webhook_url
from services.logging_config import ServiceLogger

logger = ServiceLogger('ZapierWebhookService')

# 지원 이벤트 목록
SUPPORTED_EVENTS = [
    'content.generated',
    'content.failed',
    'anomaly.detected',
    'digest.created',
    'ab_test.significant',
    'cost.threshold_exceeded',
]


class ZapierWebhookService:
    """
    이벤트별 웹훅 URL 분리 지원 Zapier 웹훅 서비스

    각 이벤트 타입에 서로 다른 Zapier Zap URL을 매핑할 수 있음.
    """

    def __init__(self):
        # event_type → WebhookService
        self._webhooks: dict[str, WebhookService] = {}
        # 글로벌 폴백 웹훅 (이벤트별 URL이 없을 때)
        self._fallback: WebhookService | None = None

    def register(self, event_type: str, url: str, enabled: bool = True) -> bool:
        """
        특정 이벤트에 웹훅 URL 등록

        Args:
            event_type: 이벤트 유형 (SUPPORTED_EVENTS 중 하나)
            url: Zapier Webhook URL
            enabled: 활성화 여부

        Returns:
            등록 성공 여부
        """
        if event_type not in SUPPORTED_EVENTS:
            logger.warning(f'지원하지 않는 이벤트: {event_type}')
            return False
        if not _validate_webhook_url(url):
            logger.warning(f'안전하지 않은 URL: {url}')
            return False
        self._webhooks[event_type] = WebhookService(url=url, enabled=enabled)
        logger.info(f'웹훅 등록: {event_type} → {url[:40]}...')
        return True

    def register_fallback(self, url: str, enabled: bool = True) -> bool:
        """글로벌 폴백 웹훅 등록"""
        if not _validate_webhook_url(url):
            logger.warning(f'안전하지 않은 폴백 URL: {url}')
            return False
        self._fallback = WebhookService(url=url, enabled=enabled)
        return True

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """이벤트 발행 — 등록된 웹훅으로 비동기 전송"""
        webhook = self._webhooks.get(event_type)
        if webhook and webhook.enabled:
            webhook.send(event_type, data)
            return
        # 폴백
        if self._fallback and self._fallback.enabled:
            self._fallback.send(event_type, data)

    def emit_content_generated(self, title: str, style: str, model: str,
                                tokens: int, cost_usd: float = 0.0) -> None:
        """콘텐츠 생성 완료 이벤트"""
        self.emit('content.generated', {
            'title': title,
            'style': style,
            'model': model,
            'tokens': tokens,
            'cost_usd': cost_usd,
        })

    def emit_content_failed(self, error: str, style: str, model: str) -> None:
        """콘텐츠 생성 실패 이벤트"""
        self.emit('content.failed', {
            'error': error,
            'style': style,
            'model': model,
        })

    def emit_anomaly(self, metric: str, value: float, z_score: float) -> None:
        """이상 탐지 이벤트"""
        self.emit('anomaly.detected', {
            'metric': metric,
            'value': value,
            'z_score': z_score,
        })

    def emit_cost_threshold(self, current_cost_usd: float, threshold_usd: float) -> None:
        """비용 임계값 초과 이벤트"""
        self.emit('cost.threshold_exceeded', {
            'current_cost_usd': current_cost_usd,
            'threshold_usd': threshold_usd,
        })

    def list_registered(self) -> list[dict]:
        """등록된 웹훅 목록 반환 (URL 마스킹)"""
        result = []
        for event, webhook in self._webhooks.items():
            url = webhook.url
            masked = url[:20] + '...' if len(url) > 20 else url
            result.append({'event': event, 'url_masked': masked, 'enabled': webhook.enabled})
        if self._fallback:
            url = self._fallback.url
            masked = url[:20] + '...' if len(url) > 20 else url
            result.append({'event': 'fallback', 'url_masked': masked, 'enabled': self._fallback.enabled})
        return result

    def get_supported_events(self) -> list[str]:
        """지원되는 이벤트 타입 목록 반환"""
        return list(SUPPORTED_EVENTS)
