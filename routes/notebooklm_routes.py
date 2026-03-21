"""NotebookLM API 라우트."""
from flask import Blueprint, jsonify, request

from services.notebooklm.notebooklm_service import NotebookLmService

notebooklm_bp = Blueprint('notebooklm', __name__, url_prefix='/api/notebooklm')

_service = NotebookLmService()


@notebooklm_bp.route('/auth-check', methods=['GET'])
def auth_check():
    """NotebookLM 인증 상태 확인."""
    result = _service.check_auth()
    status_code = 200 if result.get('valid') else 401
    return jsonify(result), status_code


@notebooklm_bp.route('/generate', methods=['POST'])
def generate():
    """NotebookLM 콘텐츠 생성 요청."""
    data = request.get_json()
    if not data:
        return jsonify({'error': '요청 본문이 비어있습니다.'}), 400

    content_type = data.get('type')
    url = data.get('url')
    source_text = data.get('source_text')

    if not content_type or not url or not source_text:
        return jsonify({'error': 'type, url, source_text 필드가 필요합니다.'}), 400

    # 인증 확인
    auth = _service.check_auth()
    if not auth.get('valid'):
        return jsonify({'error': auth.get('message', '인증이 필요합니다.')}), 401

    try:
        result = _service.generate(content_type, url, source_text)
        return jsonify(result), 202
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500


@notebooklm_bp.route('/status/<artifact_id>', methods=['GET'])
def status(artifact_id):
    """콘텐츠 생성 상태 폴링."""
    result = _service.check_status(artifact_id)
    return jsonify(result)


@notebooklm_bp.route('/download/<artifact_id>', methods=['GET'])
def download(artifact_id):
    """콘텐츠 파일 다운로드 (Phase 4에서 완성)."""
    return jsonify({'error': '다운로드 기능은 아직 구현되지 않았습니다.'}), 501
