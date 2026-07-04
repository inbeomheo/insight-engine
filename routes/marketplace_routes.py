"""
마켓플레이스 라우트 (F4-14)
프롬프트 템플릿 CRUD + 검색
"""
import logging

from flask import Blueprint, request, jsonify, g
from utils.responses import error_response, sanitize_error_for_client
from src.contexts.identity.interface.auth_decorators import require_auth

marketplace_bp = Blueprint('marketplace', __name__)
logger = logging.getLogger(__name__)


def _safe_marketplace_error(message, fallback_message):
    safe_message = sanitize_error_for_client(str(message or ''))
    if safe_message.startswith('[서버 오류]'):
        return fallback_message
    return safe_message


@marketplace_bp.route('/api/marketplace', methods=['GET'])
def list_templates():
    """템플릿 목록 (검색/필터)"""
    from services.platform.marketplace_service import marketplace_service
    category = request.args.get('category')
    query = request.args.get('q')
    templates = marketplace_service.list_templates(category=category, query=query)
    return jsonify({'templates': templates})


@marketplace_bp.route('/api/marketplace', methods=['POST'])
@require_auth
def publish_template():
    """템플릿 게시"""
    from services.platform.marketplace_service import marketplace_service
    data = request.get_json(silent=True) or {}
    try:
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
            return error_response(
                _safe_marketplace_error(
                    result['error'],
                    '[서버 오류] 템플릿 게시에 실패했습니다.'
                )
            )
        return jsonify(result), 201
    except Exception as e:
        logger.error('Marketplace publish failed: %s', e, exc_info=True)
        return error_response('[서버 오류] 템플릿 게시 중 문제가 발생했습니다.', 500)


@marketplace_bp.route('/api/marketplace/<template_id>/download', methods=['POST'])
@require_auth
def download_template(template_id):
    """템플릿 다운로드"""
    from services.platform.marketplace_service import marketplace_service
    try:
        result = marketplace_service.download_template(template_id, g.user_id)
        if 'error' in result:
            return error_response(
                _safe_marketplace_error(
                    result['error'],
                    '[서버 오류] 템플릿 다운로드에 실패했습니다.'
                ),
                404
            )
        return jsonify(result)
    except Exception as e:
        logger.error('Marketplace download failed: %s', e, exc_info=True)
        return error_response('[서버 오류] 템플릿 다운로드 중 문제가 발생했습니다.', 500)
