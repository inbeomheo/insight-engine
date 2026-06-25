"""Background job status API."""
from flask import g, jsonify

from routes.blog_routes import blog_bp
from services.core import job_service
from src.contexts.identity.interface.auth_decorators import require_auth


@blog_bp.route("/api/jobs/<job_id>", methods=["GET"])
@require_auth
def get_job(job_id: str):
    job = job_service.get_job(job_id, owner_user_id=getattr(g, "user_id", None))
    if not job:
        return jsonify({"error": "작업을 찾을 수 없습니다."}), 404
    return jsonify({"job": job})
