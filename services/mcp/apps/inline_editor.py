"""
인라인 편집 MCP App

콘텐츠를 단락 단위로 분리하여 발행 전 인라인 편집 기능을 제공합니다.
편집 이력을 메모리에 보관하여 실행 취소(undo)를 지원합니다.
"""
import html as html_lib
import logging
import re
from ..mcp_apps import BaseMCPApp

_MAX_HISTORY = 20  # 편집 이력 최대 보관 수
logger = logging.getLogger(__name__)


class InlineEditorApp(BaseMCPApp):
    """콘텐츠 단락 단위 인라인 편집 앱"""

    def __init__(self):
        # {session_id: {"sections": List[str], "history": List[List[str]]}}
        self._sessions: dict[str, dict] = {}

    def get_name(self) -> str:
        return "inline_editor"

    def get_description(self) -> str:
        return "단락 단위로 콘텐츠를 인라인 편집합니다"

    def render(self, content: dict) -> dict:
        """편집 가능한 단락 목록이 포함된 HTML을 반환합니다.

        Args:
            content: {"title": str, "content": str,
                      "session_id": str (선택, 없으면 새 세션 시작)}
        """
        session_id = content.get("session_id") or _make_session_id(content)

        # 새 세션이거나 콘텐츠가 바뀐 경우 단락 재분리
        if session_id not in self._sessions:
            raw_content = content.get("content") or ""
            sections = _split_sections(raw_content)
            self._sessions[session_id] = {
                "sections": sections,
                "history": [],
                "title": content.get("title") or "",
            }

        session = self._sessions[session_id]
        title = html_lib.escape(session["title"])
        sections = session["sections"]

        # 단락별 편집 가능한 카드 렌더링
        section_cards = ""
        for idx, sec in enumerate(sections):
            escaped = html_lib.escape(sec)
            section_cards += f"""
<div class="editor-section" data-section="{idx}" style="
  border:1px solid #d0d0d0;
  border-radius:6px;
  margin-bottom:12px;
  background:#fafafa;
  overflow:hidden;
">
  <div style="
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:6px 12px;
    background:#f0f0f0;
    font-size:0.78em;
    color:#666;
    font-family:sans-serif;
  ">
    <span>단락 {idx + 1}</span>
    <span style="color:#0066cc;cursor:pointer;"
          data-action="start_edit"
          data-section="{idx}">[편집]</span>
  </div>
  <div class="section-text" style="padding:12px 16px;line-height:1.8;font-size:15px;white-space:pre-wrap;"
       data-section="{idx}">{escaped}</div>
</div>
"""

        html_output = f"""
<div style="font-family:'Apple SD Gothic Neo','Nanum Gothic',sans-serif;max-width:760px;margin:0 auto;">
  <h2 style="font-size:1.3em;color:#222;margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid #0066cc;">
    {title}
  </h2>
  <p style="font-size:0.82em;color:#888;margin-bottom:16px;font-family:sans-serif;">
    총 {len(sections)}개 단락 · 세션 ID: {html_lib.escape(session_id)}
  </p>
  {section_cards}
</div>
"""

        actions = [
            {"action": "save_edit",  "label": "편집 저장",    "style": "primary"},
            {"action": "undo",       "label": "실행 취소",    "style": "secondary"},
            {"action": "reset",      "label": "원본으로 복원", "style": "danger"},
            {"action": "get_result", "label": "편집 결과 가져오기", "style": "success"},
        ]

        return {"html": html_output, "actions": actions}

    def handle_action(self, action: str, data: dict) -> dict:
        """편집 액션을 처리합니다.

        지원 액션:
        - save_edit:  {"session_id": str, "section": int, "new_content": str}
        - undo:       {"session_id": str}
        - reset:      {"session_id": str, "original_content": str}
        - get_result: {"session_id": str}
        """
        try:
            return self._handle_action_internal(action, data)
        except Exception as e:
            logger.error('인라인 편집 액션 처리 실패 (action=%s): %s', action, e)
            return {
                "success": False,
                "message": f"액션 처리 중 오류: {e}",
                "updated_content": None,
            }

    def _handle_action_internal(self, action: str, data: dict) -> dict:
        """실제 액션 처리 로직"""
        session_id = data.get("session_id")
        if not session_id or session_id not in self._sessions:
            return {
                "success": False,
                "message": "유효하지 않은 세션 ID입니다. render()를 먼저 호출하세요.",
                "updated_content": None,
            }

        session = self._sessions[session_id]

        if action == "save_edit":
            return self._save_edit(session, data)
        if action == "undo":
            return self._undo(session)
        if action == "reset":
            return self._reset(session, data)
        if action == "get_result":
            return self._get_result(session)

        return {
            "success": False,
            "message": f"알 수 없는 액션입니다: {action}",
            "updated_content": None,
        }

    # ── 내부 헬퍼 ──────────────────────────────────────────

    def _save_edit(self, session: dict, data: dict) -> dict:
        """단락 내용을 업데이트하고 이력을 저장합니다."""
        section_idx = data.get("section")
        new_content = data.get("new_content")

        if section_idx is None or new_content is None:
            return {
                "success": False,
                "message": "'section' 번호와 'new_content'가 필요합니다.",
                "updated_content": None,
            }

        sections = session["sections"]
        if not (0 <= int(section_idx) < len(sections)):
            return {
                "success": False,
                "message": f"단락 번호 {section_idx}가 범위를 벗어났습니다.",
                "updated_content": None,
            }

        # 이력 저장 (최대 _MAX_HISTORY 개)
        session["history"].append(list(sections))
        if len(session["history"]) > _MAX_HISTORY:
            session["history"].pop(0)

        sections[int(section_idx)] = new_content.strip()

        return {
            "success": True,
            "message": f"단락 {section_idx + 1}이 업데이트되었습니다.",
            "updated_content": {"sections": list(sections)},
        }

    def _undo(self, session: dict) -> dict:
        """마지막 편집을 취소합니다."""
        if not session["history"]:
            return {
                "success": False,
                "message": "취소할 편집 이력이 없습니다.",
                "updated_content": None,
            }

        session["sections"] = session["history"].pop()
        return {
            "success": True,
            "message": "마지막 편집이 취소되었습니다.",
            "updated_content": {"sections": list(session["sections"])},
        }

    def _reset(self, session: dict, data: dict) -> dict:
        """원본 콘텐츠로 초기화합니다."""
        original = data.get("original_content")
        if not original:
            return {
                "success": False,
                "message": "'original_content'가 필요합니다.",
                "updated_content": None,
            }

        session["history"].append(list(session["sections"]))
        session["sections"] = _split_sections(original)

        return {
            "success": True,
            "message": "원본 콘텐츠로 복원했습니다.",
            "updated_content": {"sections": list(session["sections"])},
        }

    def _get_result(self, session: dict) -> dict:
        """현재 편집된 전체 콘텐츠를 반환합니다."""
        merged = "\n\n".join(session["sections"])
        return {
            "success": True,
            "message": "편집 결과를 가져왔습니다.",
            "updated_content": {
                "title": session["title"],
                "content": merged,
            },
        }


def _split_sections(text: str) -> list:
    """텍스트를 단락 단위로 분리합니다."""
    # 빈 줄 2개 이상으로 분리 (마크다운 단락 기준)
    parts = re.split(r"\n{2,}", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _make_session_id(content: dict) -> str:
    """콘텐츠 기반 결정적 세션 ID를 생성합니다."""
    import hashlib
    key = (content.get("title") or "") + (content.get("content") or "")[:200]
    return hashlib.md5(key.encode()).hexdigest()[:12]
