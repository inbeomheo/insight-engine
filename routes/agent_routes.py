"""에이전트 API 라우트 — 대화형 콘텐츠 생성."""
from __future__ import annotations

import json
import logging
from flask import Blueprint, Response, jsonify, request, g, stream_with_context
from utils.responses import api_error

logger = logging.getLogger(__name__)

agent_bp = Blueprint("agent", __name__)


@agent_bp.route("/api/agent/chat", methods=["POST"])
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
        model = data.get("model")
        toolsets = data.get("toolsets") or ["full"]
        context = data.get("context")

        user_id = getattr(g, "user_id", None)

        agent = AIAgent(
            model=model,
            toolsets=toolsets,
            session_id=session_id,
            user_id=user_id,
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

    except Exception as e:
        logger.error("에이전트 채팅 실패: %s", e, exc_info=True)
        return api_error("[서버 오류] 에이전트 처리 중 문제가 발생했습니다.", 500)


@agent_bp.route("/api/agent/chat/stream", methods=["POST"])
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
        model = data.get("model")
        toolsets = data.get("toolsets")
        context = data.get("context")
        user_id = getattr(g, "user_id", None)

        def generate_sse():
            import queue
            import threading

            event_queue = queue.Queue()
            SENTINEL = object()

            def on_delta(text):
                event_queue.put({"type": "delta", "content": text})

            def on_tool_start(name, args):
                event_queue.put({"type": "tool_start", "name": name, "args": args})

            def on_tool_end(name, result_preview, elapsed):
                event_queue.put({
                    "type": "tool_end", "name": name,
                    "preview": result_preview[:100], "elapsed": round(elapsed, 2),
                })

            def on_iteration(current, total):
                event_queue.put({
                    "type": "progress", "iteration": current, "total": total,
                })

            agent = AIAgent(
                model=model,
                toolsets=toolsets or ["full"],
                session_id=session_id,
                user_id=user_id,
                on_stream_delta=on_delta,
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
                on_iteration=on_iteration,
            )

            result_holder = [None]
            error_holder = [None]

            def run_agent():
                try:
                    result_holder[0] = agent.run(
                        user_message=message, context=context,
                    )
                except Exception as e:
                    error_holder[0] = e
                finally:
                    event_queue.put(SENTINEL)

            thread = threading.Thread(target=run_agent, daemon=True)
            thread.start()

            # Queue 기반 이벤트 전달 (race condition 방지)
            while True:
                try:
                    event = event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if event is SENTINEL:
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 완료 이벤트
            if error_holder[0]:
                yield f"data: {json.dumps({'type': 'error', 'message': str(error_holder[0])}, ensure_ascii=False)}\n\n"
            elif result_holder[0]:
                r = result_holder[0]
                yield f"data: {json.dumps({'type': 'done', 'session_id': r.session_id, 'stats': {'tool_calls': r.tool_calls_count, 'iterations': r.iterations_used, 'elapsed': round(r.elapsed_seconds, 2)}}, ensure_ascii=False)}\n\n"

        return Response(
            stream_with_context(generate_sse()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    except Exception as e:
        logger.error("에이전트 스트리밍 실패: %s", e, exc_info=True)
        return api_error("[서버 오류] 에이전트 처리 중 문제가 발생했습니다.", 500)
