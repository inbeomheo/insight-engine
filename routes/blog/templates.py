"""프롬프트 템플릿 갤러리 API.

blog_routes.py에서 분리됨. blog_bp 데코레이터로 자동 등록되므로
routes/blog/__init__.py에서 부수효과 import만 하면 활성화된다.
"""
from flask import request, jsonify, g

from routes.blog_routes import blog_bp
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import handle_error


@blog_bp.route('/api/templates', methods=['GET'])
@require_auth
def list_templates():
    """템플릿 목록 조회 (공개 + 본인 소유)

    Query params:
        page: 페이지 번호 (기본 1)
        search: 이름/설명 검색어
    """
    from services.data.prompt_template_service import get_templates

    user_id = getattr(g, 'user_id', None)
    from utils.responses import clamp_query_int
    page = clamp_query_int(request.args.get('page'), default=1, min_val=1, max_val=10000)
    search = request.args.get('search', '').strip()

    result = get_templates(user_id=user_id, page=page, search=search)
    return jsonify(result)


@blog_bp.route('/api/templates', methods=['POST'])
@require_auth
def create_template():
    """새 템플릿 생성"""
    from services.data.prompt_template_service import create_template as svc_create

    user_id = getattr(g, 'user_id', None)
    data = request.get_json(silent=True) or {}

    # 필수 필드 검증
    name = (data.get('name') or '').strip()
    prompt_text = (data.get('prompt_text') or '').strip()

    if not name:
        return jsonify({'error': '템플릿 이름을 입력하세요.'}), 400
    if not prompt_text:
        return jsonify({'error': '프롬프트를 입력하세요.'}), 400
    if len(name) > 50:
        return jsonify({'error': '이름은 50자 이내로 입력하세요.'}), 400
    if len(prompt_text) > 5000:
        return jsonify({'error': '프롬프트는 5000자 이내로 입력하세요.'}), 400

    try:
        template = svc_create(user_id=user_id, data={
            'name': name,
            'description': (data.get('description') or '').strip()[:200],
            'prompt_text': prompt_text,
            'style_base': data.get('style_base', 'blog_seo'),
            'is_public': bool(data.get('is_public', False)),
        })
    except ValueError as e:
        return handle_error(str(e))

    if template is None:
        return jsonify({'error': '템플릿 저장에 실패했습니다.'}), 500

    return jsonify(template), 201


@blog_bp.route('/api/templates/<template_id>', methods=['PUT'])
@require_auth
def update_template(template_id: str):
    """템플릿 수정 (소유자만)"""
    from services.data.prompt_template_service import update_template as svc_update

    user_id = getattr(g, 'user_id', None)
    data = request.get_json(silent=True) or {}

    # 수정 가능한 필드 검증
    update_data = {}
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name:
            return jsonify({'error': '이름을 입력하세요.'}), 400
        if len(name) > 50:
            return jsonify({'error': '이름은 50자 이내로 입력하세요.'}), 400
        update_data['name'] = name

    if 'description' in data:
        update_data['description'] = (data.get('description') or '').strip()[:200]

    if 'prompt_text' in data:
        prompt_text = (data['prompt_text'] or '').strip()
        if not prompt_text:
            return jsonify({'error': '프롬프트를 입력하세요.'}), 400
        if len(prompt_text) > 5000:
            return jsonify({'error': '프롬프트는 5000자 이내로 입력하세요.'}), 400
        update_data['prompt_text'] = prompt_text

    if 'style_base' in data:
        update_data['style_base'] = data['style_base']

    if 'is_public' in data:
        update_data['is_public'] = bool(data['is_public'])

    result = svc_update(template_id=template_id, user_id=user_id, data=update_data)
    if result is None:
        return jsonify({'error': '템플릿을 찾을 수 없거나 수정 권한이 없습니다.'}), 404

    return jsonify(result)


@blog_bp.route('/api/templates/<template_id>', methods=['DELETE'])
@require_auth
def delete_template(template_id: str):
    """템플릿 삭제 (소유자만)"""
    from services.data.prompt_template_service import delete_template as svc_delete

    user_id = getattr(g, 'user_id', None)
    success = svc_delete(template_id=template_id, user_id=user_id)

    if not success:
        return jsonify({'error': '템플릿을 찾을 수 없거나 삭제 권한이 없습니다.'}), 404

    return jsonify({'success': True})


@blog_bp.route('/api/templates/<template_id>/use', methods=['POST'])
@require_auth
def use_template(template_id: str):
    """템플릿 사용 (사용 횟수 증가 + 내용 반환)"""
    from services.data.prompt_template_service import get_template_by_id, increment_usage

    user_id = getattr(g, 'user_id', None)
    template = get_template_by_id(template_id=template_id, user_id=user_id)

    if template is None:
        return jsonify({'error': '템플릿을 찾을 수 없습니다.'}), 404

    # 비동기적으로 사용 횟수 증가 (실패해도 무방)
    try:
        increment_usage(template_id)
    except Exception:
        pass

    return jsonify(template)
