"""NotebookLM API 라우트."""
import os
from flask import Blueprint, g, jsonify, request, send_file

from extensions import limiter
from services.usage import capture_usage_charge_callback, require_usage
from services.usage.usage_lock import UsageLockUnavailable
from services.notebooklm.notebooklm_service import (
    ARTIFACT_NOT_FOUND_MESSAGE,
    ARTIFACT_NOT_READY_MESSAGE,
    NotebookLmService,
)
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error, api_error_from_exception

notebooklm_bp = Blueprint('notebooklm', __name__, url_prefix='/api/notebooklm')

_service = NotebookLmService()


@notebooklm_bp.route('/auth-check', methods=['GET'])
@limiter.limit('10/minute')
@require_auth
def auth_check():
    """NotebookLM 인증 상태 확인."""
    result = _service.check_auth()
    if result.get('valid'):
        return jsonify(result), 200

    # 이 요청은 Insight Engine 자체에는 이미 인증된 상태다. NotebookLM CLI의
    # 별도 인증 누락을 앱 access token 오류(401)로 오인하지 않도록 구분한다.
    payload = dict(result)
    payload['code'] = 'NOTEBOOKLM_AUTH_REQUIRED'
    return jsonify(payload), 424


@notebooklm_bp.route('/generate', methods=['POST'])
@limiter.limit('3/minute')
@require_auth
@require_usage
def generate():
    """NotebookLM 콘텐츠 생성 요청."""
    data = request.get_json()
    if not data:
        return api_error('요청 본문이 비어있습니다.', 400)

    content_type = data.get('type')
    url = data.get('url')
    source_text = data.get('source_text')

    if not content_type or not url or not source_text:
        return api_error('type, url, source_text 필드가 필요합니다.', 400)

    # 인증 확인
    auth = _service.check_auth()
    if not auth.get('valid'):
        return api_error(
            auth.get('message', 'NotebookLM 인증이 필요합니다.'),
            424,
            'NOTEBOOKLM_AUTH_REQUIRED',
        )

    try:
        result = _service.generate(
            content_type,
            url,
            source_text,
            user_id=getattr(g, 'user_id', None),
            on_cost_start=capture_usage_charge_callback(),
        )
        return jsonify(result), 202
    except UsageLockUnavailable:
        raise
    except ValueError as e:
        return api_error(str(e), 400)
    except RuntimeError as e:
        return api_error_from_exception(e, '[서버 오류] NotebookLM 콘텐츠 생성 중 문제가 발생했습니다.')


@notebooklm_bp.route('/status/<artifact_id>', methods=['GET'])
@limiter.limit('30/minute')
@require_auth
def status(artifact_id):
    """콘텐츠 생성 상태 폴링."""
    result = _service.check_status(artifact_id, user_id=getattr(g, 'user_id', None))
    return jsonify(result)


@notebooklm_bp.route('/download/<artifact_id>', methods=['GET'])
@limiter.limit('10/minute')
@require_auth
def download(artifact_id):
    """콘텐츠 파일 다운로드."""
    try:
        file_path = _service.download(artifact_id, user_id=getattr(g, 'user_id', None))
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
        )
    except RuntimeError as e:
        # 존재 여부 자체가 다른 사용자에게 노출되지 않도록 404로 통일한다.
        if str(e).startswith(ARTIFACT_NOT_FOUND_MESSAGE):
            return api_error(ARTIFACT_NOT_FOUND_MESSAGE, 404)
        # 생성이 끝나지 않은 artifact 다운로드 요청은 클라이언트 오류다.
        if str(e).startswith(ARTIFACT_NOT_READY_MESSAGE):
            return api_error(ARTIFACT_NOT_READY_MESSAGE, 400)
        return api_error_from_exception(e, '[서버 오류] 파일 다운로드 중 문제가 발생했습니다.')
