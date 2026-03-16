"""
콘텐츠 미리보기 MCP App

플랫폼별(네이버 블로그, WordPress, 티스토리, Medium) 레이아웃으로
발행 전 콘텐츠 미리보기를 제공합니다.
"""
import logging
import html as html_lib
from ..mcp_apps import BaseMCPApp

logger = logging.getLogger(__name__)

# 플랫폼별 스타일 정의
_PLATFORM_STYLES: dict[str, dict] = {
    "naver_blog": {
        "label": "네이버 블로그",
        "bg": "#FFFFFF",
        "font_family": "'Nanum Gothic', 'Apple SD Gothic Neo', sans-serif",
        "title_color": "#1EC800",
        "body_color": "#333333",
        "max_width": "740px",
        "padding": "20px",
        "line_height": "1.8",
        "font_size": "15px",
    },
    "wordpress": {
        "label": "WordPress",
        "bg": "#FFFFFF",
        "font_family": "'Georgia', serif",
        "title_color": "#1d2327",
        "body_color": "#444444",
        "max_width": "800px",
        "padding": "32px",
        "line_height": "1.75",
        "font_size": "16px",
    },
    "tistory": {
        "label": "티스토리",
        "bg": "#FAFAFA",
        "font_family": "'Apple SD Gothic Neo', 'Nanum Gothic', sans-serif",
        "title_color": "#FF6B35",
        "body_color": "#3d3d3d",
        "max_width": "720px",
        "padding": "24px",
        "line_height": "1.9",
        "font_size": "15px",
    },
    "medium": {
        "label": "Medium",
        "bg": "#FFFFFF",
        "font_family": "'Medium Content Serif Font', 'Georgia', serif",
        "title_color": "#242424",
        "body_color": "#292929",
        "max_width": "740px",
        "padding": "40px 20px",
        "line_height": "2.0",
        "font_size": "18px",
    },
}

_DEFAULT_PLATFORM = "naver_blog"


class ContentPreviewApp(BaseMCPApp):
    """플랫폼별 레이아웃으로 콘텐츠를 미리보기하는 앱"""

    def get_name(self) -> str:
        return "content_preview"

    def get_description(self) -> str:
        return "플랫폼별 레이아웃으로 발행 전 콘텐츠를 미리봅니다"

    def render(self, content: dict) -> dict:
        """플랫폼별 스타일이 적용된 HTML 미리보기를 반환합니다.

        Args:
            content: {"title": str, "content": str, "html": str,
                      "platform": str (선택, 기본 naver_blog)}
        """
        try:
            return self._render_internal(content)
        except Exception as e:
            logger.error('콘텐츠 미리보기 렌더링 실패: %s', e)
            return {"html": f"<p>미리보기 생성 실패: {e}</p>", "actions": []}

    def _render_internal(self, content: dict) -> dict:
        """실제 렌더링 로직"""
        platform = content.get("platform", _DEFAULT_PLATFORM)
        style = _PLATFORM_STYLES.get(platform, _PLATFORM_STYLES[_DEFAULT_PLATFORM])

        title = html_lib.escape(content.get("title") or "제목 없음")
        # html 필드가 있으면 사용, 없으면 content를 단락으로 변환
        body_html = content.get("html") or _text_to_html(content.get("content") or "")

        preview_html = f"""
<div style="
  background:{style['bg']};
  font-family:{style['font_family']};
  color:{style['body_color']};
  max-width:{style['max_width']};
  margin:0 auto;
  padding:{style['padding']};
  line-height:{style['line_height']};
  font-size:{style['font_size']};
  border:1px solid #e0e0e0;
  border-radius:8px;
  box-shadow:0 2px 8px rgba(0,0,0,0.06);
">
  <div style="font-size:0.75em;color:#888;margin-bottom:12px;font-family:sans-serif;">
    {html_lib.escape(style['label'])} 미리보기
  </div>
  <h1 style="
    color:{style['title_color']};
    font-size:1.6em;
    font-weight:700;
    margin:0 0 20px;
    line-height:1.35;
    border-bottom:2px solid {style['title_color']}22;
    padding-bottom:12px;
  ">{title}</h1>
  <div class="preview-body" style="word-break:break-word;">
    {body_html}
  </div>
</div>
"""

        # 플랫폼 전환 액션 목록
        actions = [
            {
                "action": f"switch_platform:{pid}",
                "label": f"{info['label']}으로 미리보기",
                "style": "secondary",
            }
            for pid, info in _PLATFORM_STYLES.items()
            if pid != platform
        ]

        return {"html": preview_html, "actions": actions}

    def handle_action(self, action: str, data: dict) -> dict:
        """플랫폼 전환 액션을 처리합니다.

        지원 액션:
        - switch_platform:<platform_id>  : 미리보기 플랫폼 변경
        """
        if action.startswith("switch_platform:"):
            platform_id = action.split(":", 1)[1]
            if platform_id not in _PLATFORM_STYLES:
                return {
                    "success": False,
                    "message": f"지원하지 않는 플랫폼입니다: {platform_id}",
                    "updated_content": None,
                }
            # 플랫폼 전환: 클라이언트가 새 platform으로 render()를 다시 호출해야 함
            return {
                "success": True,
                "message": f"{_PLATFORM_STYLES[platform_id]['label']} 미리보기로 전환했습니다.",
                "updated_content": {"platform": platform_id},
            }

        return {
            "success": False,
            "message": f"알 수 없는 액션입니다: {action}",
            "updated_content": None,
        }


def _text_to_html(text: str) -> str:
    """일반 텍스트를 단락 HTML로 변환합니다."""
    if not text.strip():
        return "<p>내용이 없습니다.</p>"
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "".join(f"<p>{html_lib.escape(p)}</p>" for p in paragraphs)
