"""공유 페이지 저장/렌더링 서비스.

생성 결과를 토큰 기반 정적 JSON으로 저장하고, 공개 보기용 HTML을 렌더링한다.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Mapping

from bs4 import BeautifulSoup
from utils.runtime_paths import app_data_path

try:
    import markdown as _markdown
except Exception:  # pragma: no cover - 배포 환경에서 markdown이 없을 때만 fallback
    _markdown = None

_ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "br", "strong", "em", "b", "i", "u", "s",
    "ul", "ol", "li", "a", "img", "table", "thead", "tbody", "tr", "th", "td", "blockquote",
    "pre", "code", "span", "div", "hr", "sup", "sub", "mark",
}
_ALLOWED_ATTRS = {
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "title"},
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
    "span": {"class"},
    "div": {"class"},
    "code": {"class"},
    "pre": {"class"},
}
_DEFAULT_SHARE_DIR = Path(os.getenv("SHARE_PAGE_DIR") or app_data_path("shared_pages"))


def _safe_token(token: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", token or ""):
        raise ValueError("유효하지 않은 공유 ID입니다.")
    return token


def sanitize_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in list(soup.find_all(True)):
        if tag.name not in _ALLOWED_TAGS:
            tag.decompose()
            continue
        allowed = _ALLOWED_ATTRS.get(tag.name, set())
        attrs = dict(tag.attrs)
        for attr, value in attrs.items():
            if attr not in allowed:
                del tag.attrs[attr]
                continue
            if attr in {"href", "src"}:
                value_str = " ".join(value) if isinstance(value, list) else str(value)
                if value_str.lower().startswith(("javascript:", "data:text/html")):
                    del tag.attrs[attr]
        if tag.name == "a" and tag.get("href"):
            tag.attrs["target"] = "_blank"
            tag.attrs["rel"] = "noopener noreferrer"
    return str(soup)


def html_from_content(content: str) -> str:
    if _markdown is not None:
        return _markdown.markdown(content or "", extensions=["tables", "fenced_code", "nl2br"])
    return f"<pre>{escape(content or '')}</pre>"


def _preview_text(content: str, limit: int = 180) -> str:
    text = re.sub(r"<[^>]+>", " ", content or "")
    text = re.sub(r"[#>*_`\[\]()]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def public_origin() -> str:
    for key in ("PUBLIC_ORIGIN", "INSIGHT_BASE_URL", "APP_BASE_URL"):
        value = (os.getenv(key) or "").strip().rstrip("/")
        if value:
            return value
    return ""


class SharePageStore:
    def __init__(self, directory: str | os.PathLike[str] = _DEFAULT_SHARE_DIR, origin: str | None = None):
        self.directory = Path(directory)
        self.origin = (origin if origin is not None else public_origin()).rstrip("/")

    def _path(self, share_id: str) -> Path:
        return self.directory / f"{_safe_token(share_id)}.json"

    def create(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        self.directory.mkdir(parents=True, exist_ok=True)
        share_id = secrets.token_urlsafe(12)
        raw_html = str(payload.get("html") or "") or html_from_content(str(payload.get("content") or ""))
        item = {
            "id": share_id,
            "title": str(payload.get("title") or "공유 콘텐츠")[:160],
            "content": str(payload.get("content") or ""),
            "html": sanitize_html(raw_html),
            "url": str(payload.get("url") or ""),
            "style": str(payload.get("style") or ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        item["share_url"] = f"{self.origin}/share/{share_id}" if self.origin else f"/share/{share_id}"
        path = self._path(share_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return item

    def get(self, share_id: str) -> dict[str, Any]:
        path = self._path(share_id)
        if not path.exists():
            raise FileNotFoundError(share_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        data["html"] = sanitize_html(str(data.get("html") or html_from_content(str(data.get("content") or ""))))
        data["share_url"] = data.get("share_url") or (
            f"{self.origin}/share/{data['id']}" if self.origin else f"/share/{data['id']}"
        )
        return data


def render_share_html(item: Mapping[str, Any]) -> str:
    title = escape(str(item.get("title") or "공유 콘텐츠"))
    body = sanitize_html(str(item.get("html") or html_from_content(str(item.get("content") or ""))))
    source_url = escape(str(item.get("url") or ""), quote=True)
    created_at = escape(str(item.get("created_at") or ""))
    description = escape(_preview_text(str(item.get("content") or body)), quote=True)
    source_link = (
        f'<a class="source" href="{source_url}" target="_blank" rel="noopener noreferrer">원본 열기</a>'
        if source_url else ""
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="article">
  <style>
    :root {{ color-scheme: light dark; --bg:#0f1115; --card:#171a21; --text:#f4f4f5; --muted:#a1a1aa; --accent:#8b5cf6; }}
    @media (prefers-color-scheme: light) {{ :root {{ --bg:#f8fafc; --card:#fff; --text:#111827; --muted:#6b7280; }} }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height:1.72; }}
    main {{ width:min(880px, calc(100% - 32px)); margin:40px auto; background:var(--card); border:1px solid color-mix(in srgb, var(--muted) 24%, transparent); border-radius:24px; padding:32px; box-shadow:0 24px 80px rgba(0,0,0,.18); }}
    header {{ margin-bottom:28px; border-bottom:1px solid color-mix(in srgb, var(--muted) 20%, transparent); padding-bottom:20px; }}
    h1,h2,h3 {{ line-height:1.28; }}
    a {{ color:var(--accent); }}
    img {{ max-width:100%; border-radius:16px; }}
    pre {{ overflow:auto; padding:16px; border-radius:14px; background:rgba(127,127,127,.13); }}
    blockquote {{ border-left:4px solid var(--accent); margin-left:0; padding-left:16px; color:var(--muted); }}
    table {{ border-collapse:collapse; width:100%; display:block; overflow:auto; }}
    th,td {{ border:1px solid color-mix(in srgb, var(--muted) 30%, transparent); padding:8px 10px; }}
    .meta {{ color:var(--muted); font-size:14px; display:flex; gap:12px; flex-wrap:wrap; }}
    .source {{ text-decoration:none; font-weight:700; }}
  </style>
</head>
<body>
  <main>
    <header>
      <p class="meta"><span>Insight Engine 공유 페이지</span><span>{created_at}</span>{source_link}</p>
      <h1>{title}</h1>
    </header>
    <article>{body}</article>
  </main>
</body>
</html>"""
