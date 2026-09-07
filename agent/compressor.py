"""
컨텍스트 압축기 — 5단계 알고리즘

Hermes Agent 패턴:
1. 도구 결과 프루닝 (LLM 호출 없이, 200자 이상 옛 결과 → 플레이스홀더)
2. 헤드 보호 (시스템 프롬프트 + 첫 교환 유지)
3. 테일 보호 (최근 ~20K 토큰 유지)
4. 미들 턴 구조화 요약 (LLM 호출)
5. 반복 압축 시 이전 요약 업데이트
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

# 기본값
DEFAULT_TOOL_RESULT_MAX_LEN = 200
DEFAULT_TAIL_TOKENS = 20_000
DEFAULT_SUMMARY_BUDGET_RATIO = 0.2
MAX_SUMMARY_TOKENS = 12_000

# 요약 마커
SUMMARY_MARKER = "[컨텍스트 요약]"


def compress_messages(
    messages: List[Dict[str, Any]],
    target_tokens: int,
    model: Optional[str] = None,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> List[Dict[str, Any]]:
    """메시지 리스트를 압축합니다.

    Args:
        messages: 원본 메시지 리스트
        target_tokens: 목표 토큰 수
        model: 요약에 사용할 모델 (None이면 기본값)
        on_cost_start: 실제 LiteLLM 호출 직전 실행할 비용 콜백

    Returns:
        압축된 메시지 리스트
    """
    if not messages:
        return messages

    # 1단계: 도구 결과 프루닝
    pruned = _prune_tool_results(messages)

    # 토큰 추정
    estimated = _estimate_tokens(pruned)
    if estimated <= target_tokens:
        logger.debug("1단계 프루닝만으로 충분: %d → %d tokens", estimated, target_tokens)
        return pruned

    # 2단계 + 3단계: 헤드/테일 보호, 미들 추출
    head, middle, tail = _split_head_middle_tail(pruned)

    if not middle:
        # 미들이 없으면 더 이상 압축 불가
        return pruned

    # 4단계: 미들 턴 구조화 요약
    existing_summary = _find_existing_summary(middle)
    summary = _summarize_middle(
        middle,
        existing_summary,
        model,
        on_cost_start=on_cost_start,
    )

    # 요약 메시지로 교체
    summary_msg = {
        "role": "assistant",
        "content": f"{SUMMARY_MARKER}\n{summary}",
    }

    result = head + [summary_msg] + tail

    compressed_tokens = _estimate_tokens(result)
    logger.info(
        "컨텍스트 압축 완료: %d → %d tokens (%.0f%% 감소)",
        estimated, compressed_tokens,
        (1 - compressed_tokens / max(estimated, 1)) * 100,
    )

    return result


def _prune_tool_results(
    messages: List[Dict],
    max_len: int = DEFAULT_TOOL_RESULT_MAX_LEN,
    protect_recent: int = 6,
) -> List[Dict]:
    """도구 결과를 프루닝합니다 (LLM 호출 없음).

    최근 N개 메시지는 보호하고, 나머지 도구 결과 중
    max_len 초과하는 것을 플레이스홀더로 교체합니다.
    """
    if len(messages) <= protect_recent:
        return messages

    result = []
    cutoff = len(messages) - protect_recent

    for i, msg in enumerate(messages):
        if i < cutoff and msg.get("role") == "tool":
            content = msg.get("content", "")
            if len(content) > max_len:
                # 핵심 정보 보존: JSON이면 키만, 텍스트면 앞부분
                preview = _extract_preview(content, max_len)
                msg = {**msg, "content": f"{preview}\n... [결과 축약: {len(content)}자 → {len(preview)}자]"}
        result.append(msg)

    return result


def _extract_preview(content: str, max_len: int) -> str:
    """콘텐츠에서 핵심 미리보기를 추출합니다."""
    # JSON 결과면 키 목록 + 첫 값
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            keys = list(data.keys())[:5]
            preview = json.dumps({k: str(data[k])[:50] for k in keys}, ensure_ascii=False)
            return preview[:max_len]
        if isinstance(data, list):
            return json.dumps(data[:2], ensure_ascii=False)[:max_len]
    except (json.JSONDecodeError, TypeError):
        pass

    # 일반 텍스트
    return content[:max_len]


def _split_head_middle_tail(
    messages: List[Dict],
    tail_count: int = 10,
) -> tuple:
    """메시지를 헤드/미들/테일로 분리합니다.

    헤드: 시스템 프롬프트 + 첫 사용자-어시스턴트 교환
    테일: 최근 tail_count 메시지
    미들: 나머지
    """
    # 헤드: system + 첫 번째 user + 첫 번째 assistant
    head_end = 1  # 최소 system
    for i in range(1, min(len(messages), 6)):
        head_end = i + 1
        if messages[i].get("role") == "assistant" and messages[i].get("content"):
            break

    # 테일
    tail_start = max(head_end, len(messages) - tail_count)

    head = messages[:head_end]
    middle = messages[head_end:tail_start]
    tail = messages[tail_start:]

    return head, middle, tail


def _find_existing_summary(middle: List[Dict]) -> Optional[str]:
    """미들에서 기존 요약을 찾습니다."""
    for msg in middle:
        content = msg.get("content", "")
        if SUMMARY_MARKER in content:
            return content.replace(SUMMARY_MARKER, "").strip()
    return None


def _summarize_middle(
    middle: List[Dict],
    existing_summary: Optional[str] = None,
    model: Optional[str] = None,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> str:
    """미들 턴을 구조화 요약합니다 (LLM 호출).

    구조:
    - Goal: 사용자가 달성하려는 것
    - Progress: 지금까지 완료된 작업
    - Decisions: 내린 결정과 이유
    - Files: 읽거나 수정한 파일
    - Next Steps: 다음에 해야 할 것
    """
    # 미들 턴을 텍스트로 변환
    middle_text = _messages_to_text(middle)

    # 기존 요약이 있으면 업데이트 프롬프트
    if existing_summary:
        prompt = (
            "이전 대화 요약을 업데이트하세요. 새로운 정보를 반영하되 중요한 이전 정보는 유지하세요.\n\n"
            f"## 이전 요약\n{existing_summary}\n\n"
            f"## 새로운 대화\n{middle_text}\n\n"
            "다음 구조로 요약하세요:\n"
            "- **Goal**: 사용자가 달성하려는 것\n"
            "- **Progress**: 완료된 작업\n"
            "- **Decisions**: 내린 결정과 이유\n"
            "- **Key Data**: 중요한 데이터/결과 요약\n"
            "- **Next Steps**: 다음 단계"
        )
    else:
        prompt = (
            "다음 대화 내용을 구조화된 요약으로 작성하세요. "
            "중요한 사실과 결정은 반드시 포함하세요.\n\n"
            f"{middle_text}\n\n"
            "다음 구조로 요약하세요:\n"
            "- **Goal**: 사용자가 달성하려는 것\n"
            "- **Progress**: 완료된 작업\n"
            "- **Decisions**: 내린 결정과 이유\n"
            "- **Key Data**: 중요한 데이터/결과 요약\n"
            "- **Next Steps**: 다음 단계"
        )

    try:
        from litellm import completion

        summary_model = model or "gemini/gemini-3.1-flash-lite-preview"
        if on_cost_start is not None:
            on_cost_start()
        resp = completion(
            model=summary_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_SUMMARY_TOKENS,
            temperature=0.3,
            timeout=60,
        )
        return resp.choices[0].message.content or "요약 생성 실패"
    except UsageLockUnavailable:
        # 비용 잠금 소유권을 잃은 뒤 무비용 폴백 성공으로
        # 처리하면 상위 예약이 잘못 환불될 수 있다.
        raise
    except Exception as exc:
        logger.error(
            "컨텍스트 요약 실패 (type=%s)",
            type(exc).__name__,
        )
        # 폴백: 단순 텍스트 추출
        return _fallback_summary(middle)


def _messages_to_text(messages: List[Dict], max_total: int = 8000) -> str:
    """메시지 리스트를 요약용 텍스트로 변환합니다."""
    lines = []
    total = 0

    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")

        if role == "tool":
            # 도구 결과는 간략하게
            content = content[:200] if len(content) > 200 else content
            line = f"[Tool Result] {content}"
        elif role == "assistant":
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                names = [tc.get("function", {}).get("name", "?") for tc in tool_calls]
                line = f"[Assistant] 도구 호출: {', '.join(names)}"
            else:
                line = f"[Assistant] {content[:500]}"
        else:
            line = f"[{role.capitalize()}] {content[:500]}"

        total += len(line)
        if total > max_total:
            lines.append("... (이하 생략)")
            break
        lines.append(line)

    return "\n".join(lines)


def _fallback_summary(middle: List[Dict]) -> str:
    """LLM 없이 간단 요약 (폴백)."""
    tool_names = set()
    user_msgs = []

    for msg in middle:
        role = msg.get("role", "")
        if role == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tool_names.add(tc.get("function", {}).get("name", "?"))
        elif role == "user":
            content = msg.get("content", "")[:100]
            if content:
                user_msgs.append(content)

    summary_parts = []
    if user_msgs:
        summary_parts.append(f"**사용자 요청**: {'; '.join(user_msgs[:3])}")
    if tool_names:
        summary_parts.append(f"**사용된 도구**: {', '.join(sorted(tool_names))}")
    summary_parts.append(f"**턴 수**: {len(middle)}개 메시지")

    return "\n".join(summary_parts) if summary_parts else "이전 대화 내용 (요약 불가)"


def _estimate_tokens(messages: List[Dict]) -> int:
    """메시지 리스트의 토큰 수를 추정합니다 (근사치)."""
    total_chars = sum(
        len(msg.get("content", "")) + len(json.dumps(msg.get("tool_calls", []), ensure_ascii=False))
        for msg in messages
    )
    # 한국어: ~2-3 토큰/자, 영어: ~4 자/토큰
    # 보수적으로 2 토큰/자 가정
    return total_chars * 2 // 3
