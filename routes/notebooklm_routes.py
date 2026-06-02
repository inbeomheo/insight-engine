"""NotebookLM API 라우트."""
import html
import os
from flask import Blueprint, Response, jsonify, request, send_file

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
    """콘텐츠 파일 다운로드."""
    try:
        file_path = _service.download(artifact_id)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=os.path.basename(file_path),
        )
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 400


@notebooklm_bp.route('/view/<artifact_id>', methods=['GET'])
def view(artifact_id):
    """콘텐츠 파일을 브라우저에서 바로 볼 수 있게 반환."""
    try:
        file_path = _service.download(artifact_id)
        filename = os.path.basename(file_path)
        lower_name = filename.lower()

        if lower_name.endswith(('.md', '.markdown')):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                markdown_text = f.read()

            try:
                import markdown as md_lib
                body = md_lib.markdown(
                    html.escape(markdown_text),
                    extensions=['tables', 'fenced_code', 'nl2br'],
                )
            except Exception:
                body = f'<pre>{html.escape(markdown_text)}</pre>'

            title = html.escape(filename)
            return Response(f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ max-width: 860px; margin: 40px auto; padding: 0 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.7; color: #111827; }}
    pre, code {{ background: #f3f4f6; border-radius: 6px; }}
    pre {{ padding: 12px; overflow: auto; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 8px; }}
    blockquote {{ border-left: 4px solid #d1d5db; margin-left: 0; padding-left: 16px; color: #4b5563; }}
  </style>
</head>
<body>{body}</body>
</html>""", content_type='text/html; charset=utf-8')

        return send_file(
            file_path,
            as_attachment=False,
            download_name=filename,
        )
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 400
