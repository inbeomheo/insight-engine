"""
사용량 관리 서비스
비즈니스 로직 캡슐화

내부 구현은 Identity & Access BC의 게이트웨이/리포지토리에 위임하지만,
기존 시그니처(check_can_use/decrement/try_consume_atomic/get_current/is_admin_user)를
호환 유지하면서, 비용 작업용 reserve_for_request/refund_reservation 계약을 제공한다.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass

from src.contexts.identity.application.ports import (
    QuotaReservation,
    QuotaReservationConflict,
)
from src.shared.infrastructure.supabase_client import is_supabase_enabled
from src.contexts.identity.domain.constants import (
    DEFAULT_DAILY_LIMIT as MAX_USAGE_COUNT,
)
from src.contexts.identity.domain.exceptions import QuotaExceeded
from services.data.usage_admin_facade import (
    get_usage,
    is_admin,
)
from services.core.logging_config import ServiceLogger
from services.usage.usage_lock import mark_usage_accounting_unavailable

logger = ServiceLogger('UsageService')

# 관리자 더미 사용량 (무제한)
ADMIN_USAGE = {
    'usage_count': 999,
    'max_usage': 999,
    'can_use': True,
    'is_admin': True
}


class UsageAccountingUnavailable(RuntimeError):
    """운영 사용량을 원자적으로 차감할 수 없어 요청을 안전하게 완료할 수 없음."""


class InvalidIdempotencyKey(ValueError):
    """클라이언트가 전달한 멱등 키 형식이 안전하지 않음."""


class UsageReservationReplay(RuntimeError):
    """별도 HTTP 요청이 이미 존재하는 예약 키를 재사용함."""

    def __init__(self, usage: dict):
        super().__init__('같은 요청 키가 이미 처리 중이거나 처리되었습니다.')
        self.usage = usage


class InvalidIdempotencyReplay(ValueError):
    """같은 멱등 키가 다른 요청에 재사용됨."""


@dataclass(frozen=True)
class UsageReservation:
    """라우트 한 번의 선예약 상태와 응답용 사용량 정보."""

    quota: QuotaReservation | None
    usage_before: dict
    usage_after: dict
    billable: bool

    @property
    def owned(self) -> bool:
        return bool(self.billable and self.quota and getattr(self.quota, 'owned', False))


_IDEMPOTENCY_KEY_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
def _get_account_repository():
    """SupabaseAccountRepository 싱글톤 lazy import.

    상위 import 시점에 src.contexts.identity가 로드되지 않도록 함수 호출 시점에 import.
    """
    from src.contexts.identity.infrastructure.supabase_account_repository import (
        SupabaseAccountRepository,
    )
    # 매 호출마다 생성해도 stateless라 비용은 미미. 단순화를 위해 그대로 둠.
    return SupabaseAccountRepository()


def _is_admin_cached(user_id: str) -> bool:
    """is_admin 결과를 요청 스코프(flask.g)에 메모이즈한다.

    check_can_use → decrement 흐름에서 동일 요청에 ie_admins를 2~3회
    조회하던 것을 1회로 줄인다. 요청 컨텍스트 밖에서는 그대로 조회.
    """
    try:
        from flask import g, has_request_context
        if has_request_context():
            cache = getattr(g, '_is_admin_cache', None)
            if cache is None:
                cache = {}
                g._is_admin_cache = cache
            if user_id not in cache:
                cache[user_id] = is_admin(user_id)
            return cache[user_id]
    except Exception:
        pass
    return is_admin(user_id)


class UsageService:
    """사용량 관리 서비스 클래스"""

    @staticmethod
    def request_identity(user_id: str) -> tuple[str, str]:
        """현재 Flask 요청에서 저장용 멱등 키와 요청 지문을 만든다.

        원문 헤더/본문은 DB에 저장하지 않고 SHA-256(고정 길이 해시)만 사용한다.
        클라이언트 키가 없으면 사용자·메서드·경로·정규화된 JSON·쿼리 조합을
        결정적으로 해시해 동일 요청 재전송이 같은 예약을 찾도록 한다.
        """
        try:
            from flask import g, has_request_context, request
        except Exception as exc:  # pragma: no cover - Flask 자체가 없는 환경
            raise InvalidIdempotencyKey(
                '요청 컨텍스트 없이 멱등 키를 만들 수 없습니다.'
            ) from exc

        if not has_request_context():
            raise InvalidIdempotencyKey(
                '요청 컨텍스트 없이 멱등 키를 만들 수 없습니다.'
            )

        cached_identity = getattr(g, '_usage_request_identity', None)
        if cached_identity is not None:
            return cached_identity

        client_key = request.headers.get('Idempotency-Key')
        if client_key is not None:
            client_key = client_key.strip()
            if not _IDEMPOTENCY_KEY_RE.fullmatch(client_key):
                raise InvalidIdempotencyKey(
                    'Idempotency-Key는 영문자/숫자로 시작하는 1~128자의 '
                    '영문자, 숫자, 점, 밑줄, 콜론, 하이픈만 사용할 수 있습니다.'
                )

        json_body = request.get_json(silent=True)
        if json_body is not None:
            body_bytes = json.dumps(
                json_body,
                ensure_ascii=False,
                sort_keys=True,
                separators=(',', ':'),
            ).encode('utf-8')
        else:
            body_bytes = request.get_data(cache=True) or b''

        query_items = sorted((key, value) for key, value in request.args.items(multi=True))
        fingerprint_material = b'\x00'.join((
            str(user_id).encode('utf-8'),
            request.method.upper().encode('ascii', errors='ignore'),
            request.path.encode('utf-8'),
            json.dumps(query_items, separators=(',', ':')).encode('utf-8'),
            body_bytes,
        ))
        fingerprint = hashlib.sha256(fingerprint_material).hexdigest()

        if client_key:
            stored_key = 'client:' + hashlib.sha256(client_key.encode('utf-8')).hexdigest()
        else:
            # 헤더가 없으면 요청 스코프 nonce를 지문과 결합한다.
            # 같은 Flask 요청 안에서는 결정적으로 재사용되지만, 같은
            # payload의 정상적인 새 생성을 409로 막지 않는다. HTTP 재시도
            # 멱등성은 클라이언트가 Idempotency-Key를 보낸 경우에만 보장한다.
            request_nonce = secrets.token_hex(32)
            fallback_material = f'{fingerprint}:{request_nonce}'.encode('ascii')
            stored_key = 'fallback:' + hashlib.sha256(fallback_material).hexdigest()
        identity = (stored_key, fingerprint)
        g._usage_request_identity = identity
        return identity

    @staticmethod
    def reserve_for_request(user_id: str, amount: int = 1) -> UsageReservation:
        """비용 작업 전에 현재 요청의 사용량을 원자적·멱등 예약한다."""
        if not is_supabase_enabled() or not user_id:
            return UsageReservation(
                quota=None,
                usage_before=dict(ADMIN_USAGE),
                usage_after=dict(ADMIN_USAGE),
                billable=False,
            )

        if _is_admin_cached(user_id):
            return UsageReservation(
                quota=None,
                usage_before=dict(ADMIN_USAGE),
                usage_after=dict(ADMIN_USAGE),
                billable=False,
            )

        # 이전 비용 작업의 환불 응답이 유실됐다면 새 비용을 예약하기 전에
        # 같은 사용자 JWT로 멱등 환불을 재처리한다. 실패 시 과금을 더 쌓지 않는다.
        UsageService.reconcile_pending_refunds(user_id)

        idempotency_key, request_fingerprint = UsageService.request_identity(user_id)
        owner_token_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()

        try:
            from src.contexts.identity.infrastructure.supabase_account_repository import (
                AmbiguousQuotaReservation,
            )
            from src.contexts.identity.infrastructure.supabase_usage_gateway import (
                SupabaseUsageGateway,
            )
            from src.shared.domain.value_objects import AccountId

            gateway = SupabaseUsageGateway(_get_account_repository())
            quota = gateway.reserve(
                AccountId(value=user_id),
                idempotency_key,
                request_fingerprint,
                owner_token_hash,
                amount,
            )
        except AmbiguousQuotaReservation as exc:
            # 예약 RPC와 즉시 보상 RPC의 응답을 모두 잃은 경우 실제 차감 여부를
            # 추측하지 않는다. 같은 소유 토큰을 가진 합성 예약을 먼저 영속화해
            # 다음 같은 사용자 요청이 비용 작업 전에 보상하도록 한다.
            try:
                UsageService._enqueue_quota_refund(
                    user_id,
                    exc.reservation,
                    exc,
                )
            except Exception as queue_exc:
                logger.error(f"모호한 사용량 예약 영속화 실패: {queue_exc}")
            mark_usage_accounting_unavailable()
            raise UsageAccountingUnavailable(
                '사용량 예약 결과를 확인할 수 없어 복구 대기 중입니다.'
            ) from exc
        except QuotaExceeded:
            raise
        except QuotaReservationConflict as exc:
            # 클라이언트 입력 충돌은 회계 백엔드 장애가 아니다.
            raise InvalidIdempotencyReplay(
                '같은 Idempotency-Key를 다른 요청에 사용할 수 없습니다.'
            ) from exc
        except Exception as exc:
            logger.error(f"사용량 선예약 실패: {exc}")
            mark_usage_accounting_unavailable()
            raise UsageAccountingUnavailable(
                '사용량을 안전하게 예약할 수 없습니다.'
            ) from exc

        usage_after = {
            'usage_count': quota.remaining,
            'max_usage': quota.max_usage,
            'can_use': quota.remaining > 0,
            'is_admin': False,
        }
        usage_before = {
            **usage_after,
            'usage_count': min(quota.max_usage, quota.remaining + amount),
            'can_use': True,
        }
        reservation = UsageReservation(
            quota=quota,
            usage_before=usage_before,
            usage_after=usage_after,
            billable=True,
        )
        # 같은 고수준 RPC 호출의 응답 유실 재시도는 owner token이 같아 owned=True다.
        # owned=False는 별도 HTTP 요청이 기존 예약을 재생한 것이므로 비용 작업을
        # 다시 실행하지 않는다. 그렇지 않으면 한 번 차감으로 무제한 작업이 가능하다.
        if not quota.owned:
            raise UsageReservationReplay(usage_after)
        return reservation

    @staticmethod
    def refund_reservation(user_id: str, reservation: UsageReservation) -> dict:
        """실패/캐시 적중 요청이 소유한 예약만 멱등 환불한다."""
        if not reservation.billable or not reservation.quota:
            return reservation.usage_before
        if not reservation.owned:
            return reservation.usage_after

        try:
            from src.contexts.identity.infrastructure.supabase_usage_gateway import (
                SupabaseUsageGateway,
            )
            from src.shared.domain.value_objects import AccountId

            gateway = SupabaseUsageGateway(_get_account_repository())
            remaining = gateway.refund(
                AccountId(value=user_id),
                reservation.quota,
            )
            try:
                from services.usage.refund_queue import remove_refund
                remove_refund(reservation.quota.reservation_id)
            except Exception as queue_exc:
                # RPC는 이미 멱등 완료됐다. 원장 삭제 실패는 다음 재시도에서
                # 동일 환불을 다시 확인하게 두되 성공 응답을 훼손하지 않는다.
                logger.error(f"완료된 사용량 환불 원장 정리 실패: {queue_exc}")
            max_usage = reservation.usage_after.get('max_usage', MAX_USAGE_COUNT)
            return {
                'usage_count': remaining,
                'max_usage': max_usage,
                'can_use': remaining > 0,
                'is_admin': False,
            }
        except Exception as exc:
            logger.error(f"사용량 예약 환불 실패: {exc}")
            try:
                UsageService._enqueue_pending_refund(user_id, reservation, exc)
            except Exception as queue_exc:
                logger.error(f"사용량 환불 재시도 원장 기록 실패: {queue_exc}")
            mark_usage_accounting_unavailable()
            raise UsageAccountingUnavailable(
                '사용량 예약을 안전하게 환불할 수 없습니다.'
            ) from exc

    @staticmethod
    def _enqueue_pending_refund(
        user_id: str,
        reservation: UsageReservation,
        error: Exception,
    ) -> None:
        """Persist only the fields required by the idempotent refund RPC."""
        if not reservation.owned or not reservation.quota:
            return
        UsageService._enqueue_quota_refund(user_id, reservation.quota, error)

    @staticmethod
    def _enqueue_quota_refund(
        user_id: str,
        quota: QuotaReservation,
        error: Exception,
    ) -> None:
        """Persist a validated quota refund, including ambiguous reservations."""
        from services.usage.refund_queue import enqueue_refund

        enqueue_refund({
            'user_id': user_id,
            'reservation_id': quota.reservation_id,
            'idempotency_key': quota.idempotency_key,
            'request_fingerprint': quota.request_fingerprint,
            'owner_token_hash': quota.owner_token_hash,
            'amount': quota.amount,
            'remaining': quota.remaining,
            'max_usage': quota.max_usage,
        }, str(error))

    @staticmethod
    def reconcile_pending_refunds(user_id: str, limit: int = 20) -> int:
        """Retry durable refunds for the authenticated user before new billing."""
        from services.usage.refund_queue import (
            pending_refunds_for_user,
            remove_refund,
        )
        from src.contexts.identity.infrastructure.supabase_usage_gateway import (
            SupabaseUsageGateway,
        )
        from src.shared.domain.value_objects import AccountId

        try:
            jobs = pending_refunds_for_user(user_id, limit=limit)
        except Exception as exc:
            logger.error(f"사용량 환불 재시도 원장 조회 실패: {exc}")
            mark_usage_accounting_unavailable()
            raise UsageAccountingUnavailable(
                '사용량 환불 재시도 원장을 안전하게 읽을 수 없습니다.'
            ) from exc

        if not jobs:
            return 0

        gateway = SupabaseUsageGateway(_get_account_repository())
        reconciled = 0
        for job in jobs:
            try:
                # refund_queue가 저장 시점과 읽기 시점에 모두 검증하지만, 이
                # 경계에서도 변환 실패를 회계 장애로 명시해 raw KeyError/500이
                # 라우트까지 새지 않게 한다.
                quota = QuotaReservation(
                    reservation_id=job['reservation_id'],
                    idempotency_key=job['idempotency_key'],
                    request_fingerprint=job['request_fingerprint'],
                    owner_token_hash=job['owner_token_hash'],
                    amount=job['amount'],
                    remaining=job['remaining'],
                    max_usage=job['max_usage'],
                    owned=True,
                    replayed=True,
                )
                gateway.refund(AccountId(value=user_id), quota)
                remove_refund(quota.reservation_id)
                reconciled += 1
            except Exception as exc:
                logger.error(f"대기 중인 사용량 환불 재처리 실패: {exc}")
                try:
                    UsageService._enqueue_pending_refund(
                        user_id,
                        UsageReservation(
                            quota=quota,
                            usage_before={},
                            usage_after={},
                            billable=True,
                        ),
                        exc,
                    )
                except Exception as queue_exc:
                    logger.error(f"사용량 환불 재시도 상태 갱신 실패: {queue_exc}")
                mark_usage_accounting_unavailable()
                raise UsageAccountingUnavailable(
                    '대기 중인 사용량 환불을 안전하게 처리할 수 없습니다.'
                ) from exc
        return reconciled

    @staticmethod
    def refund_reservation_quietly(
        user_id: str,
        reservation: UsageReservation,
    ) -> dict:
        """기존 라우트 오류를 가리지 않도록 환불 장애를 기록하고 원래 값을 반환."""
        try:
            return UsageService.refund_reservation(user_id, reservation)
        except UsageAccountingUnavailable:
            return reservation.usage_after

    @staticmethod
    def check_can_use(user_id: str) -> tuple[bool, dict]:
        """
        사용 가능 여부 확인

        Args:
            user_id: 사용자 ID

        Returns:
            tuple: (can_use: bool, usage: dict)
        """
        if not is_supabase_enabled() or not user_id:
            logger.info("Supabase 비활성 또는 user_id 없음, ADMIN_USAGE 반환")
            return True, ADMIN_USAGE

        # 관리자는 무제한 (요청 스코프 캐시로 중복 조회 방지)
        admin_status = _is_admin_cached(user_id)
        logger.info(f"check_can_use: user_id={user_id[:8]}..., is_admin={admin_status}")
        if admin_status:
            logger.info(f"관리자 사용: {user_id[:8]}..., ADMIN_USAGE 반환")
            return True, ADMIN_USAGE

        # 조회는 기존 supabase_service.get_usage를 유지 (미마이그레이션).
        usage = get_usage(user_id)
        can_use = usage.get('can_use', False)
        logger.info(f"일반 사용자: user_id={user_id[:8]}..., usage={usage}, can_use={can_use}")

        if not can_use:
            logger.warning(f"사용량 소진: {user_id[:8]}...")

        return can_use, usage

    @staticmethod
    def decrement(user_id: str) -> dict:
        """
        사용량 차감 후 업데이트된 사용량 반환

        내부적으로 Identity BC의 SupabaseUsageGateway를 경유하여 원자적 차감.
        한도 초과/예외 시에는 기존 폴백(get_usage)을 사용해 호환성을 유지한다.

        Args:
            user_id: 사용자 ID

        Returns:
            dict: 업데이트된 사용량 정보
        """
        if not is_supabase_enabled() or not user_id:
            return ADMIN_USAGE

        if _is_admin_cached(user_id):
            return ADMIN_USAGE

        # Identity BC 게이트웨이로 차감 (원자적). 운영 차감 장애는 무료
        # 허용으로 폴백하지 않고 호출자가 503으로 처리하도록 명시적으로 전파한다.
        try:
            from src.contexts.identity.domain.exceptions import QuotaExceeded
            from src.contexts.identity.infrastructure.supabase_usage_gateway import (
                SupabaseUsageGateway,
            )
            from src.shared.domain.value_objects import AccountId

            gateway = SupabaseUsageGateway(_get_account_repository())
            try:
                remaining = gateway.check_and_consume(AccountId(value=user_id), 1)
                return {
                    'usage_count': remaining,
                    'max_usage': MAX_USAGE_COUNT,
                    'can_use': remaining > 0,
                    'is_admin': False,
                }
            except QuotaExceeded:
                # 한도 초과 — 호환을 위해 0/can_use=False dict 반환 (기존엔 get_usage 결과)
                logger.info(f"decrement: 한도 초과 {user_id[:8]}...")
                return {
                    'usage_count': 0,
                    'max_usage': MAX_USAGE_COUNT,
                    'can_use': False,
                    'is_admin': False,
                }
        except Exception as exc:
            logger.error(f"사용량 원자 차감 실패: {exc}")
            mark_usage_accounting_unavailable()
            raise UsageAccountingUnavailable(
                '사용량을 안전하게 기록할 수 없습니다.'
            ) from exc

    @staticmethod
    def try_consume_atomic(user_id: str) -> tuple[bool, dict]:
        """
        원자적으로 사용량 체크 + 차감을 시도합니다.
        Race Condition을 방지하기 위해 Identity BC 게이트웨이에 위임합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            tuple: (성공 여부, 사용량 정보)
                - 성공: (True, {'usage_count': n, 'can_use': True, 'max_usage': 20})
                - 실패: (False, {'usage_count': 0, 'can_use': False})
        """
        if not is_supabase_enabled() or not user_id:
            return True, ADMIN_USAGE

        if _is_admin_cached(user_id):
            return True, ADMIN_USAGE

        # Identity BC 게이트웨이로 위임. QuotaExceeded는 한도 초과 응답으로 변환.
        try:
            from src.contexts.identity.domain.exceptions import QuotaExceeded
            from src.shared.domain.value_objects import AccountId

            repo = _get_account_repository()
            remaining = repo.consume_quota_atomic(AccountId(value=user_id), 1)
            return True, {
                'usage_count': remaining,
                'can_use': True,
                'max_usage': MAX_USAGE_COUNT,
            }
        except Exception as exc:
            # QuotaExceeded는 lazy import이므로 isinstance 체크를 위해 한 번 더 import
            try:
                from src.contexts.identity.domain.exceptions import QuotaExceeded
                if isinstance(exc, QuotaExceeded):
                    logger.info(f"사용량 차감 실패: {user_id[:8]}... - quota_exceeded")
                    return False, {
                        'usage_count': 0,
                        'can_use': False,
                        'max_usage': MAX_USAGE_COUNT,
                    }
            except Exception:  # pragma: no cover
                pass

            logger.error(f"사용량 RPC 호출 실패: {exc}")
            mark_usage_accounting_unavailable()
            raise UsageAccountingUnavailable(
                '사용량을 안전하게 기록할 수 없습니다.'
            ) from exc

    @staticmethod
    def get_current(user_id: str) -> dict:
        """
        현재 사용량 조회

        Args:
            user_id: 사용자 ID

        Returns:
            dict: 사용량 정보
        """
        if not is_supabase_enabled() or not user_id:
            return ADMIN_USAGE

        if _is_admin_cached(user_id):
            return ADMIN_USAGE

        return get_usage(user_id)

    @staticmethod
    def is_admin_user(user_id: str) -> bool:
        """
        관리자 여부 확인

        Args:
            user_id: 사용자 ID

        Returns:
            bool: 관리자 여부
        """
        if not is_supabase_enabled() or not user_id:
            return False
        return _is_admin_cached(user_id)


# 싱글톤 인스턴스
usage_service = UsageService()
