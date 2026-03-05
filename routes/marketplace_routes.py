"""
마켓플레이스 라우트 (F4-14)
프롬프트 템플릿 CRUD + 검색
"""
from flask import Blueprint, request, jsonify, g
from utils.responses import success_response, error_response
from services.supabase_service import require_auth

marketplace_bp = Blueprint('marketplace', __name__)


@marketplace_bp.route('/api/marketplace', methods=['GET'])
def list_templates():
    """템플릿 목록 (검색/필터)"""
    from services.marketplace_service import marketplace_service
    category = request.args.get('category')
    query = request.args.get('q')
    templates = marketplace_service.list_templates(category=category, query=query)
    return jsonify({'templates': templates})


@marketplace_bp.route('/api/marketplace/<template_id>', methods=['GET'])
def get_template(template_id):
    """템플릿 상세"""
    from services.marketplace_service import marketplace_service
    template = marketplace_service.get_template(template_id)
    if not template:
        return error_response('템플릿을 찾을 수 없습니다.', 404)
    return jsonify(template)


@marketplace_bp.route('/api/marketplace', methods=['POST'])
@require_auth
def publish_template():
    """템플릿 게시"""
    from services.marketplace_service import marketplace_service
    data = request.get_json(silent=True) or {}
    result = marketplace_service.publish_template(
        author_id=g.user_id,
        title=data.get('title', ''),
        description=data.get('description', ''),
        prompt_text=data.get('prompt_text', ''),
        category=data.get('category', 'general'),
        price=float(data.get('price', 0)),
        tags=data.get('tags'),
    )
    if 'error' in result:
        return error_response(result['error'])
    return jsonify(result), 201


@marketplace_bp.route('/api/marketplace/<template_id>/download', methods=['POST'])
@require_auth
def download_template(template_id):
    """템플릿 다운로드"""
    from services.marketplace_service import marketplace_service
    result = marketplace_service.download_template(template_id, g.user_id)
    if 'error' in result:
        return error_response(result['error'], 404)
    return jsonify(result)


@marketplace_bp.route('/api/marketplace/<template_id>/rate', methods=['POST'])
@require_auth
def rate_template(template_id):
    """템플릿 평점"""
    from services.marketplace_service import marketplace_service
    data = request.get_json(silent=True) or {}
    rating = float(data.get('rating', 0))
    result = marketplace_service.rate_template(template_id, g.user_id, rating)
    if 'error' in result:
        return error_response(result['error'])
    return jsonify(result)
