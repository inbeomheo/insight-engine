"""사용자 설정 라우트 — API 키 / 커스텀 스타일 / 사용량 조회.

auth_routes.py에서 분리됨. patch 호환을 위해 모든 함수 호출은
`routes.auth_routes` namespace를 경유한다 (`_ar.get_api_keys(...)` 형식).
"""
from flask import g, jsonify

from routes import auth_routes as _ar  # patch 호환을 위한 namespace 접근
from routes.auth_routes import auth_bp
from services.data.supabase_service import require_auth


def _mask_api_key(key):
    """API 키 마스킹 (보안 강화)

    기존: 8자 + 4자 = 12자 노출
    변경: 4자 + 2자 = 6자 노출
    """
    if not key:
        return None
    if len(key) <= 8:
        return '****'
    return f'{key[:4]}...{key[-2:]}'


# ── API 키 관리 ─────────────────────────────────────────


@auth_bp.route('/api/user/keys', methods=['GET'])
@require_auth
def get_user_keys():
    """사용자 API 키 조회"""
    keys = _ar.get_api_keys(g.user_id)
    masked_keys = {
        k: _mask_api_key(v) if k != 'selectedProvider' else v
        for k, v in keys.items()
    }
    return jsonify({'keys': masked_keys, 'selectedProvider': keys.get('selectedProvider')})


@auth_bp.route('/api/user/keys', methods=['POST'])
@require_auth
def save_user_keys():
    """사용자 API 키 저장"""
    if _ar.save_api_keys(g.user_id, _ar._get_json_data()):
        return _ar._success_response()
    return _ar._error_response('API 키 저장에 실패했습니다.', 500)


# ── 커스텀 스타일 관리 ───────────────────────────────────


@auth_bp.route('/api/user/styles', methods=['GET'])
@require_auth
def get_user_styles():
    """사용자 커스텀 스타일 조회"""
    return jsonify({'styles': _ar.get_custom_styles(g.user_id)})


@auth_bp.route('/api/user/styles', methods=['POST'])
@require_auth
def save_user_style():
    """사용자 커스텀 스타일 저장"""
    if _ar.save_custom_style(g.user_id, _ar._get_json_data()):
        return _ar._success_response()
    return _ar._error_response('스타일 저장에 실패했습니다.', 500)


@auth_bp.route('/api/user/styles/<style_id>', methods=['DELETE'])
@require_auth
def delete_user_style(style_id):
    """사용자 커스텀 스타일 삭제"""
    if _ar.delete_custom_style(g.user_id, style_id):
        return _ar._success_response()
    return _ar._error_response('삭제에 실패했습니다.', 500)


# ── 사용량 조회 ──────────────────────────────────────────


@auth_bp.route('/api/user/usage', methods=['GET'])
@require_auth
def get_user_usage():
    """사용자 사용량 조회 (남은 횟수, 최대 횟수)"""
    usage = _ar.get_usage(g.user_id)
    # 관리자 여부 추가
    usage['is_admin'] = _ar.is_admin(g.user_id)
    return jsonify(usage)
