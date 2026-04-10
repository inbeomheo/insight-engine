"""
쿠폰 서비스 (F4-12)
쿠폰 코드 CRUD + 적용/검증
"""
import uuid
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger

logger = ServiceLogger('CouponService')


class CouponService:
    """쿠폰 코드 생성/검증/적용"""

    def __init__(self):
        self._coupons: dict[str, dict] = {}
        self._redemptions: list[dict] = []

    def create_coupon(
        self,
        code: str | None = None,
        discount_type: str = 'percentage',
        discount_value: float = 10.0,
        max_uses: int = 100,
        expires_at: str | None = None,
    ) -> dict:
        """쿠폰 생성

        Args:
            code: 쿠폰 코드 (None이면 자동 생성)
            discount_type: 'percentage' 또는 'fixed'
            discount_value: 할인 값 (% 또는 원)
            max_uses: 최대 사용 횟수
            expires_at: 만료일 (ISO 8601)
        """
        if discount_type not in ('percentage', 'fixed'):
            return {'error': "discount_type은 'percentage' 또는 'fixed'만 허용됩니다."}

        try:
            if discount_type == 'percentage' and not (0 < discount_value <= 100):
                return {'error': '퍼센트 할인은 1~100 사이여야 합니다.'}

            code = code or f'COUP-{uuid.uuid4().hex[:6].upper()}'

            if code in self._coupons:
                return {'error': f'이미 존재하는 쿠폰 코드입니다: {code}'}

            coupon = {
                'code': code,
                'discount_type': discount_type,
                'discount_value': discount_value,
                'max_uses': max_uses,
                'used_count': 0,
                'is_active': True,
                'expires_at': expires_at,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            self._coupons[code] = coupon
            logger.info(f"쿠폰 생성: {code} ({discount_type} {discount_value})")
            return coupon
        except Exception as e:
            logger.error("create_coupon 실패: %s", e, exc_info=True)
            return {}

    def validate_coupon(self, code: str) -> dict:
        """쿠폰 유효성 검증"""
        try:
            coupon = self._coupons.get(code)
            if not coupon:
                return {'valid': False, 'reason': '존재하지 않는 쿠폰입니다.'}

            if not coupon['is_active']:
                return {'valid': False, 'reason': '비활성화된 쿠폰입니다.'}

            if coupon['used_count'] >= coupon['max_uses']:
                return {'valid': False, 'reason': '사용 한도를 초과했습니다.'}

            if coupon['expires_at']:
                expires = datetime.fromisoformat(coupon['expires_at'])
                if datetime.now(timezone.utc) > expires:
                    return {'valid': False, 'reason': '만료된 쿠폰입니다.'}

            return {'valid': True, 'coupon': coupon}
        except Exception as e:
            logger.error("validate_coupon 실패: %s", e, exc_info=True)
            return {}

    def redeem_coupon(self, code: str, user_id: str, original_amount: float) -> dict:
        """쿠폰 적용 (할인 계산 + 사용 처리)"""
        try:
            validation = self.validate_coupon(code)
            if not validation['valid']:
                return {'error': validation['reason']}

            coupon = validation['coupon']
            if coupon['discount_type'] == 'percentage':
                discount = original_amount * (coupon['discount_value'] / 100)
            else:
                discount = min(coupon['discount_value'], original_amount)

            final_amount = original_amount - discount
            coupon['used_count'] += 1

            self._redemptions.append({
                'code': code,
                'user_id': user_id,
                'discount': discount,
                'redeemed_at': datetime.now(timezone.utc).isoformat(),
            })

            return {
                'original': original_amount,
                'discount': discount,
                'final': final_amount,
                'coupon_code': code,
            }
        except Exception as e:
            logger.error("redeem_coupon 실패: %s", e, exc_info=True)
            return {}

    def deactivate_coupon(self, code: str) -> dict:
        """쿠폰 비활성화"""
        try:
            coupon = self._coupons.get(code)
            if not coupon:
                return {'error': '쿠폰을 찾을 수 없습니다.'}

            coupon['is_active'] = False
            return coupon
        except Exception as e:
            logger.error("deactivate_coupon 실패: %s", e, exc_info=True)
            return {}

    def list_coupons(self) -> list[dict]:
        """전체 쿠폰 목록"""
        try:
            return list(self._coupons.values())
        except Exception as e:
            logger.error("list_coupons 실패: %s", e, exc_info=True)
            return []


coupon_service = CouponService()
