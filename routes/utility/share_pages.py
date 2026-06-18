"""공유 페이지 API/공개 보기 라우트."""
from __future__ import annotations

import os
from pathlib import Path

from flask import Response, current_app, jsonify, request

from routes.blog_routes import blog_bp
from services.content.share_page_service import SharePageStore, render_share_html
from src.contexts.identity.interface.auth_decorators import require_auth


def _share_store() -> SharePageStore:
    directory = current_app.config.get("SHARE_PAGE_DIR") or os.getenv("SHARE_PAGE_DIR") or "data/shared_pages"
    if not Path(directory).is_absolute():
        directory = str(Path(current_app.root_path) / directory)
    origin = os.getenv("PUBLIC_ORIGIN", "").rstrip("/")
    return SharePageStore(directory, origin=origin)


@blog_bp.route("/api/shares", methods=["POST"])
@require_auth
def create_share_page():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"error": "JSON 본문이 필요합니다."}), 400

    title = str(data.get("title") or "").strip()
    content = str(data.get("content") or "").strip()
    html = str(data.get("html") or "").strip()
    if not title:
        return jsonify({"error": "공유할 제목이 필요합니다."}), 400
    if not content and not html:
        return jsonify({"error": "공유할 콘텐츠가 필요합니다."}), 400

    item = _share_store().create({
        "title": title,
        "content": content,
        "html": html,
        "url": data.get("url") or "",
        "style": data.get("style") or "",
    })
    return jsonify({
        "id": item["id"],
        "share_url": item["share_url"],
        "title": item["title"],
        "created_at": item["created_at"],
    }), 201


@blog_bp.route("/api/shares/<share_id>", methods=["GET"])
def get_share_page_json(share_id: str):
    try:
        item = _share_store().get(share_id)
    except (FileNotFoundError, ValueError):
        return jsonify({"error": "공유 페이지를 찾을 수 없습니다."}), 404
    return jsonify(item)


@blog_bp.route("/share/<share_id>", methods=["GET"])
def view_share_page(share_id: str):
    try:
        item = _share_store().get(share_id)
    except (FileNotFoundError, ValueError):
        return Response("공유 페이지를 찾을 수 없습니다.", status=404, mimetype="text/plain; charset=utf-8")
    return Response(render_share_html(item), mimetype="text/html; charset=utf-8")
