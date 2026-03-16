"""
인보이스 서비스 (F4-10)
결제 내역 기반 인보이스 생성/조회
"""
import uuid
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger
import logging

logger = ServiceLogger('InvoiceService')


class InvoiceService:
    """인보이스 생성 및 관리"""

    def __init__(self):
        self._invoices: dict[str, dict] = {}

    def create_invoice(self, user_id: str, items: list[dict], currency: str = 'KRW') -> dict:
        """인보이스 생성

        Args:
            user_id: 사용자 ID
            items: [{'description': str, 'amount': int, 'quantity': int}]
            currency: 통화 코드
        """
        if not items:
            return {'error': '항목이 비어있습니다.'}

        try:
            invoice_id = f'INV-{uuid.uuid4().hex[:8].upper()}'
            total = sum(item.get('amount', 0) * item.get('quantity', 1) for item in items)

            invoice = {
                'id': invoice_id,
                'user_id': user_id,
                'items': items,
                'total': total,
                'currency': currency,
                'status': 'draft',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'paid_at': None,
            }
            self._invoices[invoice_id] = invoice
            logger.info(f"인보이스 생성: {invoice_id} ({total} {currency})")
            return invoice
        except Exception as e:
            logger.error("create_invoice 실패: %s", e, exc_info=True)
            return {}

    def get_invoice(self, invoice_id: str) -> dict | None:
        """인보이스 단건 조회"""
        try:
            return self._invoices.get(invoice_id)
        except Exception as e:
            logger.error("get_invoice 실패: %s", e, exc_info=True)
            return {}

    def list_invoices(self, user_id: str) -> list[dict]:
        """사용자의 인보이스 목록"""
        try:
            return [inv for inv in self._invoices.values() if inv['user_id'] == user_id]
        except Exception as e:
            logger.error("list_invoices 실패: %s", e, exc_info=True)
            return []

    def mark_paid(self, invoice_id: str) -> dict:
        """인보이스 결제 완료 처리"""
        try:
            invoice = self._invoices.get(invoice_id)
            if not invoice:
                return {'error': '인보이스를 찾을 수 없습니다.'}

            invoice['status'] = 'paid'
            invoice['paid_at'] = datetime.now(timezone.utc).isoformat()
            return invoice
        except Exception as e:
            logger.error("mark_paid 실패: %s", e, exc_info=True)
            return {}


invoice_service = InvoiceService()
