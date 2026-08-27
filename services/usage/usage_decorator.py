"""
사용량 체크 데코레이터
blog_routes.py의 중복 코드 제거

내부 구현은 Identity & Access BC의 어댑터에 위임된다:
- 선예약은 `UsageService.reserve_for_request` → `SupabaseUsageGateway.reserve`
  → `SupabaseAccountRepository.reserve_quota_atomic`
- 실패/캐시 환불은 같은 예약 원장의 소유 토큰을 검증하는 멱등 RPC를 사용
- 조회(`check_can_use`)는 기존 `services.data.supabase_service`를 그대로 사용
  (Phase 2-f 범위 외 — 차후 마이그레이션 예정).

외부 시그니처(@require_usage, @check_usage, get_usage_for_response)와
에러 응답 형식(`code='USAGE_LIMIT_EXCEEDED'`, 429)은 100% 기존 호환.
"""
from functools import wraps
from threading import Lock

from flask import g, has_request_context, jsonify, make_response

from src.contexts.identity.domain.exceptions import QuotaExceeded
from src.shared.infrastructure.supabase_client import is_supabase_enabled
from services.usage.usage_service import (
    ADMIN_USAGE,
    InvalidIdempotencyReplay,
    InvalidIdempotencyKey,
    MAX_USAGE_COUNT,
    UsageAccountingUnavailable,
    UsageReservationReplay,
    UsageService,
)
from services.usage.usage_lock import (
    UsageLockBusy,
    UsageLockUnavailable,
    acquire_usage_request_lock,
)
from services.core.logging_config import ServiceLogger

# Identity BC 게이트웨이 (eager import — 데코레이터 호출 경로의 위임 지점을
# 명시적으로 노출). 실제 사용은 UsageService의 예약/환불 내부에서 위임된다.
from src.contexts.identity.infrastructure.supabase_usage_gateway import (  # noqa: F401
    SupabaseUsageGateway,
)

logger = ServiceLogger('UsageDecorator')


class UsageChargeState:
    """Track whether a reserved request crossed its external cost boundary.

    A route can hand this object to worker threads that do not inherit Flask's
    request context.  The lock makes concurrent provider calls safe: once any
    worker commits the charge, later failures must not refund the reservation.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._committed = False

    def mark_committed(self) -> bool:
        """Commit the charge and return whether this call changed the state."""
        with self._lock:
            changed = not self._committed
            self._committed = True
            return changed

    @property
    def committed(self) -> bool:
        with self._lock:
            return self._committed


def mark_usage_charge_committed(state: UsageChargeState | None = None) -> bool:
    """Mark an explicit or current-request usage reservation as billable.

    Calls outside a decorated request are intentionally a no-op.  This keeps
    shared provider adapters usable from background jobs and tests that do not
    reserve user quota.
    """
    charge_state = state
    if charge_state is None and has_request_context():
        # 일반 동기 요청은 비용 직전에도 분산 임대 소유권을 확인한다.
        # 명시 state를 받은 worker는 호출자가 캡처한 임대를 검사한다.
        _ensure_usage_lease_valid(getattr(g, 'usage_lease', None))
        charge_state = getattr(g, 'usage_charge_state', None)
    if charge_state is None:
        return False
    charge_state.mark_committed()
    return True


def capture_usage_charge_callback():
    """Capture the current reservation and lease for a worker-thread callback."""
    if not has_request_context():
        return None
    charge_state = getattr(g, 'usage_charge_state', None)
    if charge_state is None:
        return None
    usage_lease = getattr(g, 'usage_lease', None)

    def commit_captured_charge() -> bool:
        _ensure_usage_lease_valid(usage_lease)
        return mark_usage_charge_committed(charge_state)

    return commit_captured_charge


def _is_success_response(result) -> bool:
    """Return True when route output maps to HTTP 2xx/3xx."""
    try:
        response = make_response(result)
        return 200 <= response.status_code < 400
    except Exception:
        return False


def _ensure_usage_lease_valid(lease) -> None:
    """분산 잠금 임대 소유권 상실을 비용 작업 전에 fail-closed 처리."""
    if lease is not None and getattr(lease, 'released', False) is True:
        raise UsageLockUnavailable('이미 해제된 사용량 잠금 임대입니다.')
    if lease is not None and getattr(lease, 'lost', False) is True:
        reason = getattr(lease, 'lost_reason', None)
        raise UsageLockUnavailable(
            f'사용량 잠금 임대 소유권을 상실했습니다: {reason or "unknown"}'
        )


def _release_usage_lease(lease) -> None:
    """즉시 2회 뒤에도 실패하면 유한한 백그라운드 정리를 예약한다."""
    if lease is None:
        return
    for _attempt in range(2):
        lease.release()
        if (
            getattr(lease, 'released', False) is True
            or getattr(lease, 'lost', False) is True
        ):
            return
    schedule_retry = getattr(lease, 'schedule_release_retry', None)
    if callable(schedule_retry):
        try:
            schedule_retry()
        except Exception as exc:
            # Redis TTL은 마지막 안전장치로 남는다. 정리 스레드 생성 실패가
            # 원래 라우트 응답을 바꾸지는 않되 운영 로그로 드러낸다.
            logger.error(f'사용량 잠금 백그라운드 해제 예약 실패: {exc}')


def check_usage(f):
    """
    사용량 체크 데코레이터 (차감하지 않음)
    사용 불가 시 429 응답 반환

    Usage:
        @require_auth
        @check_usage
        def my_route():
            # g.usage에 현재 사용량 정보가 설정됨
            # g.is_admin에 관리자 여부가 설정됨
            pass
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Supabase 비활성화 시 통과
        if not is_supabase_enabled():
            g.usage = ADMIN_USAGE
            g.is_admin = False
            return f(*args, **kwargs)

        user_id = getattr(g, 'user_id', None)
        if not user_id:
            g.usage = ADMIN_USAGE
            g.is_admin = False
            return f(*args, **kwargs)

        # 사용량 체크
        can_use, usage = UsageService.check_can_use(user_id)
        g.usage = usage
        g.is_admin = usage.get('is_admin', False)

        if not can_use:
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'code': 'USAGE_LIMIT_EXCEEDED',
                'usage': usage
            }), 429

        return f(*args, **kwargs)
    return decorated


def require_usage(f):
    """
    사용량 선예약 + 실패 시 자동 환불 데코레이터
    콘텐츠 생성 등 실제 리소스 소비 API에 사용

    Usage:
        @require_auth
        @require_usage
        def generate():
            # 함수 실행 전에 사용량 예약
            # g.usage에 차감 전 사용량 정보
            # g.updated_usage에 차감 후 사용량 정보 (함수 실행 후)
            pass

    Note:
        - 관리자는 예약/차감하지 않음
        - 비용 함수 실행 전에 DB 원장 기반 예약을 확보함
        - 외부 비용 경계 전의 실패 응답/예외/캐시 적중만 멱등 환불함
        - 성공한 비용 작업 뒤에는 추가 DB 정산을 하지 않아 성공을 503으로 바꾸지 않음
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Supabase 비활성화 시 통과
        if not is_supabase_enabled():
            g.usage = ADMIN_USAGE
            g.updated_usage = ADMIN_USAGE
            g.is_admin = False
            return f(*args, **kwargs)

        user_id = getattr(g, 'user_id', None)
        if not user_id:
            g.usage = ADMIN_USAGE
            g.updated_usage = ADMIN_USAGE
            g.is_admin = False
            return f(*args, **kwargs)

        lease = None
        reservation = None
        charge_state = None
        try:
            # 동일 사용자의 비용 요청은 직렬화하되, 실제 안전성은 DB 원장의
            # 원자적 예약/고유 키가 보장한다.
            lease = acquire_usage_request_lock(user_id)
            g.usage_lease = lease
            _ensure_usage_lease_valid(lease)

            try:
                reservation = UsageService.reserve_for_request(user_id)
            except Exception:
                # 예약 자체가 성공하지 않았으므로 비용 함수를 절대 실행하지 않는다.
                raise

            g.usage_reservation = reservation
            charge_state = UsageChargeState()
            g.usage_charge_state = charge_state
            g.usage = reservation.usage_before
            # 라우트 내부의 get_usage_for_response()는 기존과 같이 차감 전 값을
            # 보게 하고, 라우트 종료 뒤 최종 정산 값을 채운다.
            g.updated_usage = None
            g.is_admin = reservation.usage_after.get('is_admin', False)

            try:
                # 예약 RPC 도중 임대가 유실됐으면 비용 작업 진입 전에 자체 예약만 환불.
                _ensure_usage_lease_valid(lease)
            except UsageLockUnavailable:
                g.updated_usage = UsageService.refund_reservation_quietly(
                    user_id,
                    reservation,
                )
                raise

            try:
                result = f(*args, **kwargs)
            except Exception:
                # 외부 비용 경계를 넘은 후의 실패는 이미 비용이 발생했을
                # 수 있으므로 예약 차감을 유지한다. 예외는 환불 오류로 가리지 않는다.
                if charge_state.committed:
                    logger.warning(
                        '비용 확정 뒤 skip_usage_decrement가 설정되어 예약 차감을 유지합니다.'
                    )
                    g.updated_usage = reservation.usage_after
                else:
                    g.updated_usage = UsageService.refund_reservation_quietly(
                        user_id,
                        reservation,
                    )
                raise

            if g.is_admin:
                g.updated_usage = ADMIN_USAGE
            elif getattr(g, 'skip_usage_decrement', False):
                # 캐시/짧은 콘텐츠 바이패스는 비용 미발생이므로 환불 실패를
                # 명시적 503으로 처리해 조용히 과금된 성공 응답을 내보내지 않는다.
                if charge_state.committed:
                    g.updated_usage = reservation.usage_after
                else:
                    g.updated_usage = UsageService.refund_reservation(
                        user_id,
                        reservation,
                    )
            elif not _is_success_response(result):
                if charge_state.committed:
                    g.updated_usage = reservation.usage_after
                else:
                    g.updated_usage = UsageService.refund_reservation_quietly(
                        user_id,
                        reservation,
                    )
            else:
                g.updated_usage = reservation.usage_after

            # 비용 성공 경로는 선예약으로 정산 완료. 후속 RPC 없이 원래 응답 보존.
            return result
        except InvalidIdempotencyKey as exc:
            return jsonify({
                'error': str(exc),
                'code': 'INVALID_IDEMPOTENCY_KEY',
            }), 400
        except (InvalidIdempotencyReplay, UsageReservationReplay) as exc:
            payload = {
                'error': str(exc),
                'code': 'IDEMPOTENCY_REPLAY',
            }
            if isinstance(exc, UsageReservationReplay):
                payload['usage'] = exc.usage
            return jsonify(payload), 409
        except QuotaExceeded:
            usage = {
                'usage_count': 0,
                'max_usage': getattr(g, 'usage', {}).get(
                    'max_usage',
                    MAX_USAGE_COUNT,
                ),
                'can_use': False,
                'is_admin': False,
            }
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'code': 'USAGE_LIMIT_EXCEEDED',
                'usage': usage,
            }), 429
        except UsageLockBusy:
            return jsonify({
                'error': '이 계정의 콘텐츠 생성 요청이 이미 진행 중입니다.',
                'code': 'USAGE_REQUEST_IN_PROGRESS',
            }), 409
        except UsageLockUnavailable as exc:
            logger.error(f'사용량 분산 잠금 사용 불가: {exc}')
            return jsonify({
                'error': '사용량 확인 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
                'code': 'USAGE_LOCK_UNAVAILABLE',
            }), 503
        except UsageAccountingUnavailable as exc:
            logger.error(f'사용량 차감 사용 불가: {exc}')
            return jsonify({
                'error': '사용량 기록 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
                'code': 'USAGE_ACCOUNTING_UNAVAILABLE',
            }), 503
        finally:
            if lease is not None:
                _release_usage_lease(lease)
    return decorated


def get_usage_for_response() -> dict:
    """
    응답에 포함할 사용량 정보 반환
    데코레이터 사용 후 호출

    Returns:
        dict: 업데이트된 사용량 또는 현재 사용량
    """
    return getattr(g, 'updated_usage', None) or getattr(g, 'usage', ADMIN_USAGE)
