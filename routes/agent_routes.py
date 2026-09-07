"""에이전트 API 라우트 — 대화형 콘텐츠 생성."""
from __future__ import annotations

import json
import logging
import queue
import threading
from flask import (
    Blueprint,
    Response,
    copy_current_request_context,
    g,
    jsonify,
    request,
    stream_with_context,
)
from extensions import limiter
from services.core.ai_service import resolve_public_model
from services.usage import UsageService, require_usage
from services.usage.usage_decorator import (
    UsageChargeState,
    _ensure_usage_lease_valid,
    _release_usage_lease,
    capture_usage_charge_callback,
    mark_usage_charge_committed,
)
from services.usage.usage_lock import (
    UsageLockBusy,
    UsageLockUnavailable,
    acquire_usage_request_lock,
)
from services.usage.usage_service import (
    InvalidIdempotencyKey,
    InvalidIdempotencyReplay,
    MAX_USAGE_COUNT,
    UsageAccountingUnavailable,
    UsageReservationReplay,
)
from src.contexts.identity.interface.auth_decorators import require_auth
from src.contexts.identity.domain.exceptions import QuotaExceeded
from src.shared.infrastructure.supabase_client import is_supabase_enabled
from utils.responses import api_error

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__)
_TOOL_ERROR_PREVIEW = "도구 실행 중 문제가 발생했습니다."


def _start_agent_thread(worker: threading.Thread) -> None:
    """Start the agent worker through a narrow, testable boundary."""
    worker.start()


def _public_tool_preview(result_preview) -> str:
    """도구 오류 상세를 SSE에 싣지 않고 성공 결과만 짧게 노출한다."""
    text = str(result_preview or "")
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError):
        parsed = None

    if isinstance(parsed, dict) and parsed.get("error"):
        return _TOOL_ERROR_PREVIEW
    normalized = text.lstrip().lower()
    if normalized.startswith((
        "error",
        "exception",
        "도구 실행 실패",
        '{"error"',
        "{'error'",
    )):
        return _TOOL_ERROR_PREVIEW
    return text[:100]


@agent_bp.route("/api/agent/chat", methods=["POST"])
@limiter.limit("5/minute")
@require_auth
@require_usage
def agent_chat():
    """에이전트와 대화형 콘텐츠 생성.

    Request:
        {
            "message": "이 영상으로 블로그 글 써줘: https://youtube.com/...",
            "session_id": null,       // 새 세션이면 null
            "model": null,            // null이면 기본 모델
            "toolsets": ["role_writer"],  // null이면 "full"
        }

    Response:
        {
            "content": "생성된 콘텐츠...",
            "session_id": "uuid",
            "tool_calls_count": 5,
            "iterations_used": 3,
            "elapsed_seconds": 12.5,
        }
    """
    try:
        from agent import AIAgent

        data = request.json or {}
        message = data.get("message", "").strip()
        if not message:
            return api_error("메시지가 필요합니다.", 400)

        session_id = data.get("session_id")
        from config import AGENT_DEFAULT_MODEL
        try:
            model = resolve_public_model(
                data.get("model"), AGENT_DEFAULT_MODEL, allow_auto=False
            )
        except ValueError as exc:
            return api_error(str(exc), 400, 'UNSUPPORTED_MODEL')
        toolsets = data.get("toolsets") or ["full"]
        context = data.get("context")

        user_id = getattr(g, "user_id", None)

        agent = AIAgent(
            model=model,
            toolsets=toolsets,
            session_id=session_id,
            user_id=user_id,
            on_cost_start=capture_usage_charge_callback(),
        )

        response = agent.run(user_message=message, context=context)

        return jsonify({
            "content": response.content,
            "session_id": response.session_id,
            "tool_calls_count": response.tool_calls_count,
            "iterations_used": response.iterations_used,
            "elapsed_seconds": round(response.elapsed_seconds, 2),
            "metadata": response.metadata,
        })

    except UsageLockUnavailable:
        # @require_usage가 잠금 장애를 일관된 503으로 변환하고 미확정 예약을
        # 환불할 수 있도록 비용 경계 예외를 일반 500으로 낮추지 않는다.
        raise
    except Exception as exc:
        logger.error(
            "에이전트 채팅 실패 (type=%s)",
            type(exc).__name__,
        )
        return api_error("[서버 오류] 에이전트 처리 중 문제가 발생했습니다.", 500)


@agent_bp.route("/api/agent/chat/stream", methods=["POST"])
@limiter.limit("5/minute")
@require_auth
def agent_chat_stream():
    """에이전트 스트리밍 대화 (SSE).

    Request: /api/agent/chat와 동일

    Response: text/event-stream
        data: {"type": "delta", "content": "텍스트..."}
        data: {"type": "tool_start", "name": "analyze_readability", "args": {...}}
        data: {"type": "tool_end", "name": "analyze_readability", "elapsed": 1.2}
        data: {"type": "done", "session_id": "uuid", "stats": {...}}
    """
    try:
        from agent import AIAgent

        data = request.json or {}
        message = data.get("message", "").strip()
        if not message:
            return api_error("메시지가 필요합니다.", 400)

        session_id = data.get("session_id")
        from config import AGENT_DEFAULT_MODEL
        try:
            model = resolve_public_model(
                data.get("model"), AGENT_DEFAULT_MODEL, allow_auto=False
            )
        except ValueError as exc:
            return api_error(str(exc), 400, 'UNSUPPORTED_MODEL')
        toolsets = data.get("toolsets")
        context = data.get("context")
        user_id = getattr(g, "user_id", None)
        usage_enabled = bool(user_id) and is_supabase_enabled()

        # 요청 컨텍스트가 살아 있을 때 검증된 JWT로 선예약한다. 백그라운드
        # 작업에 들어간 뒤 차감하면 성공 결과가 무료가 되거나 이중 차감될 수 있다.
        usage_lease = None
        usage_reservation = None
        if usage_enabled:
            try:
                usage_lease = acquire_usage_request_lock(user_id)
                _ensure_usage_lease_valid(usage_lease)
                usage_reservation = UsageService.reserve_for_request(user_id)
                _ensure_usage_lease_valid(usage_lease)
            except Exception as exc:
                if usage_reservation is not None:
                    UsageService.refund_reservation_quietly(
                        user_id,
                        usage_reservation,
                    )
                _release_usage_lease(usage_lease)

                if isinstance(exc, InvalidIdempotencyKey):
                    return api_error(str(exc), 400, 'INVALID_IDEMPOTENCY_KEY')
                if isinstance(exc, (InvalidIdempotencyReplay, UsageReservationReplay)):
                    payload = {
                        'error': str(exc),
                        'code': 'IDEMPOTENCY_REPLAY',
                    }
                    if isinstance(exc, UsageReservationReplay):
                        payload['usage'] = exc.usage
                    return jsonify(payload), 409
                if isinstance(exc, QuotaExceeded):
                    return jsonify({
                        'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                        'code': 'USAGE_LIMIT_EXCEEDED',
                        'usage': {
                            'usage_count': 0,
                            'max_usage': MAX_USAGE_COUNT,
                            'can_use': False,
                            'is_admin': False,
                        },
                    }), 429
                if isinstance(exc, UsageLockBusy):
                    return api_error(
                        '이 계정의 콘텐츠 생성 요청이 이미 진행 중입니다.',
                        409,
                        'USAGE_REQUEST_IN_PROGRESS',
                    )
                if isinstance(exc, UsageLockUnavailable):
                    logger.error(
                        "에이전트 스트리밍 사용량 잠금 사용 불가 (type=%s)",
                        type(exc).__name__,
                    )
                    return api_error(
                        '사용량 확인 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
                        503,
                        'USAGE_LOCK_UNAVAILABLE',
                    )
                if isinstance(exc, UsageAccountingUnavailable):
                    logger.error(
                        "에이전트 스트리밍 사용량 예약 불가 (type=%s)",
                        type(exc).__name__,
                    )
                    return api_error(
                        '사용량 기록 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
                        503,
                        'USAGE_ACCOUNTING_UNAVAILABLE',
                    )
                raise

        # AI 작업은 백그라운드 스레드에서 실행한다. 해당 스레드가 사용량 잠금을
        # 직접 보유하므로 클라이언트가 SSE 연결을 끊어도 작업과 차감이 끝날 때까지
        # 같은 사용자의 두 번째 비용 요청이 진입하지 못한다.
        event_queue = queue.Queue(maxsize=256)
        client_disconnected = threading.Event()
        sentinel = object()
        result_holder = [None]
        error_holder = [None]
        usage_charge_state = UsageChargeState()

        def enqueue_event(event):
            while not client_disconnected.is_set():
                try:
                    event_queue.put(event, timeout=0.1)
                    return
                except queue.Full:
                    continue

        def on_delta(text):
            enqueue_event({"type": "delta", "content": text})

        def on_tool_start(name, args):
            enqueue_event({"type": "tool_start", "name": name, "args": args})

        def on_tool_end(name, result_preview, elapsed):
            enqueue_event({
                "type": "tool_end", "name": name,
                "preview": _public_tool_preview(result_preview),
                "elapsed": round(elapsed, 2),
            })

        def on_iteration(current, total):
            enqueue_event({
                "type": "progress", "iteration": current, "total": total,
            })

        def execute_agent():
            def commit_agent_charge():
                # 반복 LLM 호출마다 임대를 재검사한다. 첫 호출만 상태를
                # 확정하지만 이후 호출도 잃은 임대로 새 비용을 시작하지 않는다.
                _ensure_usage_lease_valid(usage_lease)
                mark_usage_charge_committed(usage_charge_state)

            agent = AIAgent(
                model=model,
                toolsets=toolsets or ["full"],
                session_id=session_id,
                user_id=user_id,
                on_stream_delta=on_delta,
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
                on_iteration=on_iteration,
                on_cost_start=commit_agent_charge,
            )
            result = agent.run(user_message=message, context=context)
            result_holder[0] = result

        access_token = getattr(g, 'access_token', None)

        @copy_current_request_context
        def run_agent():
            # 복사된 요청 컨텍스트의 g는 새 객체이므로, 실패 환불 RPC가 사용할
            # 검증된 사용자와 access token을 명시적으로 전달한다.
            g.user_id = user_id
            if access_token:
                g.access_token = access_token
            try:
                _ensure_usage_lease_valid(usage_lease)
                execute_agent()
            except Exception as exc:
                logger.error(
                    "에이전트 스트리밍 실행 실패 (type=%s)",
                    type(exc).__name__,
                )
                if usage_reservation is not None and not usage_charge_state.committed:
                    UsageService.refund_reservation_quietly(
                        user_id,
                        usage_reservation,
                    )
                error_holder[0] = exc
            finally:
                _release_usage_lease(usage_lease)
                enqueue_event(sentinel)

        thread = threading.Thread(target=run_agent, daemon=True)
        try:
            _start_agent_thread(thread)
        except Exception:
            # 예약은 요청 스레드에서 이미 확보됐다. OS/thread 런타임이 작업
            # 시작 자체를 거부하면 worker의 finally가 실행되지 않으므로 여기서
            # 미확정 예약과 임대를 직접 정리한다.
            if usage_reservation is not None and not usage_charge_state.committed:
                UsageService.refund_reservation_quietly(
                    user_id,
                    usage_reservation,
                )
            _release_usage_lease(usage_lease)
            raise

        def generate_sse():
            try:
                while True:
                    try:
                        event = event_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if event is sentinel:
                        break
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if error_holder[0]:
                    error_event = {
                        "type": "error",
                        "message": "[서버 오류] 에이전트 처리 중 문제가 발생했습니다.",
                    }
                    yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
                elif result_holder[0]:
                    r = result_holder[0]
                    done_event = {
                        "type": "done",
                        "session_id": r.session_id,
                        "stats": {
                            "tool_calls": r.tool_calls_count,
                            "iterations": r.iterations_used,
                            "elapsed": round(r.elapsed_seconds, 2),
                        },
                    }
                    yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"
            finally:
                # 연결이 끊기면 콜백은 더 이상 큐를 채우지 않지만 AI 작업은 끝까지
                # 실행되어 성공 시 차감되고, 작업 스레드가 보유한 잠금도 정상 해제된다.
                client_disconnected.set()

        return Response(
            stream_with_context(generate_sse()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    except Exception as exc:
        logger.error(
            "에이전트 스트리밍 실패 (type=%s)",
            type(exc).__name__,
        )
        return api_error("[서버 오류] 에이전트 처리 중 문제가 발생했습니다.", 500)
