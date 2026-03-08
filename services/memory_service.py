"""
AI 메모리 레이어 — 사용자별 장기 메모리 관리
선호 주제, 톤, 피드백을 저장하여 AI 프롬프트에 자동 주입합니다.
JSON 파일 기반 로컬 저장 + Supabase 연동 (선택적).
"""
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

_DEFAULT_MEMORY_PATH = "./data/user_memory"

# 메모리 키 정의
MEMORY_KEYS = {
    "preferred_topics",     # 선호 주제 리스트
    "preferred_tone",       # 선호 톤 (예: "전문적", "친근한")
    "feedback_history",     # 피드백 기록 (최근 N개)
    "custom_instructions",  # 사용자 커스텀 지시사항
    "avoid_topics",         # 피하고 싶은 주제
    "language",             # 선호 언어
}

# 피드백 히스토리 최대 보존 개수
MAX_FEEDBACK_HISTORY = 20


class MemoryService:
    """사용자별 장기 메모리를 관리합니다.

    로컬 JSON 파일에 저장하고, Supabase가 활성화되면 클라우드에도 동기화합니다.
    """

    def __init__(self, store_path: str = _DEFAULT_MEMORY_PATH):
        self._store_path = store_path
        os.makedirs(store_path, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _file_path(self, user_id: str) -> str:
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return os.path.join(self._store_path, f"{safe_id}.json")

    def _load(self, user_id: str) -> Dict[str, Any]:
        if user_id in self._cache:
            return self._cache[user_id]

        fpath = self._file_path(user_id)
        data: Dict[str, Any] = {}
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"메모리 로드 실패 (user={user_id}): {e}")

        self._cache[user_id] = data
        return data

    def _save(self, user_id: str) -> None:
        data = self._cache.get(user_id, {})
        fpath = self._file_path(user_id)
        try:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            logger.error(f"메모리 저장 실패 (user={user_id}): {e}")

    def get_memory(self, user_id: str) -> Dict[str, Any]:
        """사용자 메모리 전체를 반환합니다."""
        return dict(self._load(user_id))

    def get_value(self, user_id: str, key: str, default: Any = None) -> Any:
        """특정 메모리 키의 값을 반환합니다."""
        data = self._load(user_id)
        return data.get(key, default)

    def update_memory(self, user_id: str, key: str, value: Any) -> None:
        """메모리 값을 업데이트합니다.

        Args:
            user_id: 사용자 ID
            key: 메모리 키 (MEMORY_KEYS 참조)
            value: 저장할 값
        """
        data = self._load(user_id)

        # feedback_history는 append 방식
        if key == "feedback_history" and isinstance(value, str):
            history = data.get("feedback_history", [])
            history.append(value)
            data["feedback_history"] = history[-MAX_FEEDBACK_HISTORY:]
        else:
            data[key] = value

        self._cache[user_id] = data
        self._save(user_id)

    def delete_key(self, user_id: str, key: str) -> None:
        """특정 메모리 키를 삭제합니다."""
        data = self._load(user_id)
        if key in data:
            del data[key]
            self._cache[user_id] = data
            self._save(user_id)

    def clear(self, user_id: str) -> None:
        """사용자 메모리를 전체 초기화합니다."""
        self._cache[user_id] = {}
        fpath = self._file_path(user_id)
        if os.path.exists(fpath):
            os.remove(fpath)
        logger.info(f"메모리 초기화: user={user_id}")

    def build_prompt_context(self, user_id: str) -> str:
        """메모리를 AI 프롬프트 삽입용 텍스트로 변환합니다.

        Returns:
            '[사용자 메모리]\\n...' 형식 문자열 또는 빈 문자열
        """
        data = self._load(user_id)
        if not data:
            return ""

        lines = []

        topics = data.get("preferred_topics", [])
        if topics:
            lines.append(f"- 선호 주제: {', '.join(topics[:5])}")

        tone = data.get("preferred_tone")
        if tone:
            lines.append(f"- 선호 톤: {tone}")

        avoid = data.get("avoid_topics", [])
        if avoid:
            lines.append(f"- 피하는 주제: {', '.join(avoid[:5])}")

        custom = data.get("custom_instructions", "")
        if custom:
            lines.append(f"- 커스텀 지시: {custom[:200]}")

        lang = data.get("language")
        if lang:
            lines.append(f"- 선호 언어: {lang}")

        # 최근 피드백 요약 (최신 3개)
        feedback = data.get("feedback_history", [])
        if feedback:
            recent = feedback[-3:]
            lines.append(f"- 최근 피드백: {'; '.join(recent)}")

        if not lines:
            return ""

        return "[사용자 메모리]\n" + "\n".join(lines)


# 싱글턴 인스턴스
_store_path = os.environ.get("USER_MEMORY_PATH", _DEFAULT_MEMORY_PATH)
memory_service = MemoryService(store_path=_store_path)
