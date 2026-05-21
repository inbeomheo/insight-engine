"""기타 통합 — OpenAPI 문서, 앱 피드백, OAuth 2.0 공급자."""
from flask import request, jsonify, current_app, g

from routes.blog_routes import blog_bp
from services.data.supabase_service import require_auth


# ── OpenAPI 문서 (F7-08) ──────────────────────────────────────


@blog_bp.route('/api/openapi.json', methods=['GET'])
def openapi_spec():
    """OpenAPI 3.0 스펙 JSON 반환"""
    from services.data.openapi_service import build_openapi_spec
    server_url = request.host_url.rstrip('/')
    spec = build_openapi_spec(server_url=server_url)
    return jsonify(spec)


@blog_bp.route('/api/docs', methods=['GET'])
def api_docs():
    """Swagger UI 렌더링"""
    spec_url = '/api/openapi.json'
    html = f"""<!DOCTYPE html>
<html>
<head>
  <title>Insight Engine API 문서</title>
  <meta charset="utf-8"/>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({{
      url: '{spec_url}',
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
      layout: 'BaseLayout'
    }});
  </script>
</body>
</html>"""
    return html, 200, {'Content-Type': 'text/html'}


# ── 앱 피드백 (F7-24) ──────────────────────────────────────


@blog_bp.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """앱 내 피드백 수신"""
    data = request.get_json(silent=True) or {}
    feedback_type = data.get('type', 'general')
    rating = data.get('rating', 0)
    comment = data.get('comment', '').strip()
    page = data.get('page', '/')

    if not comment:
        return jsonify({'error': '코멘트가 필요합니다.'}), 400
    if not (1 <= int(rating) <= 5):
        return jsonify({'error': '별점은 1~5 사이여야 합니다.'}), 400

    valid_types = {'bug', 'feature', 'general'}
    if feedback_type not in valid_types:
        return jsonify({'error': f'유효하지 않은 피드백 유형: {feedback_type}'}), 400

    # 실제 운영 시 DB 저장 / Slack 알림 등으로 연결
    current_app.logger.info(
        f"[피드백] type={feedback_type}, rating={rating}, page={page}, comment={comment[:100]}"
    )
    return jsonify({'success': True, 'message': '피드백이 접수되었습니다.'})


# ── OAuth 2.0 공급자 (F7-25) ──────────────────────────────────────


@blog_bp.route('/oauth/register', methods=['POST'])
def oauth_register_client():
    """OAuth 2.0 클라이언트 등록"""
    from services.auth.oauth_provider_service import oauth_provider_service

    data = request.get_json(silent=True) or {}
    name = data.get('client_name', '').strip()
    redirect_uris = data.get('redirect_uris', [])
    scopes = data.get('scopes', ['read'])

    if not name:
        return jsonify({'error': 'client_name이 필요합니다.'}), 400
    if not redirect_uris:
        return jsonify({'error': 'redirect_uris가 필요합니다.'}), 400

    try:
        result = oauth_provider_service.register_client(name, redirect_uris, scopes)
    except Exception as e:
        current_app.logger.error('OAuth client registration failed: %s', e, exc_info=True)
        return jsonify({'error': '[서버 오류] OAuth 클라이언트 등록 중 문제가 발생했습니다.'}), 500
    return jsonify(result), 201


@blog_bp.route('/oauth/authorize', methods=['GET', 'POST'])
@require_auth
def oauth_authorize():
    """OAuth 2.0 인가 엔드포인트"""
    from services.auth.oauth_provider_service import oauth_provider_service
    from urllib.parse import urlencode

    if request.method == 'GET':
        # 인가 페이지 (실제로는 로그인 확인 후 동의 화면 표시)
        client_id = request.args.get('client_id', '')
        redirect_uri = request.args.get('redirect_uri', '')
        scope = request.args.get('scope', 'read')
        state = request.args.get('state', '')
        code_challenge = request.args.get('code_challenge', '')
        code_challenge_method = request.args.get('code_challenge_method', 'S256')

        # 인증된 사용자 ID 사용
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            return jsonify({'error': '인증이 필요합니다.'}), 401
        try:
            code = oauth_provider_service.create_authorization_code(
                client_id=client_id,
                user_id=user_id,
                scope=scope,
                redirect_uri=redirect_uri,
                code_challenge=code_challenge or None,
                code_challenge_method=code_challenge_method,
            )
        except Exception as e:
            current_app.logger.error('OAuth authorize failed: %s', e, exc_info=True)
            return jsonify({'error': '[인증 실패] OAuth 인가 처리 중 문제가 발생했습니다.'}), 500

        if not code:
            return jsonify({'error': '인가 실패 — 클라이언트 또는 redirect_uri 검증 오류'}), 400

        params = {'code': code}
        if state:
            params['state'] = state
        return jsonify({'redirect_to': f'{redirect_uri}?{urlencode(params)}'})

    return jsonify({'error': 'GET 메서드를 사용하세요.'}), 405


@blog_bp.route('/oauth/token', methods=['POST'])
def oauth_token():
    """OAuth 2.0 토큰 엔드포인트"""
    from services.auth.oauth_provider_service import oauth_provider_service

    data = request.get_json(silent=True) or request.form.to_dict()
    grant_type = data.get('grant_type', '')

    if grant_type == 'authorization_code':
        try:
            result = oauth_provider_service.exchange_code_for_token(
                code=data.get('code', ''),
                client_id=data.get('client_id', ''),
                client_secret=data.get('client_secret', ''),
                redirect_uri=data.get('redirect_uri', ''),
                code_verifier=data.get('code_verifier'),
            )
        except Exception as e:
            current_app.logger.error('OAuth token exchange failed: %s', e, exc_info=True)
            return jsonify({'error': 'server_error', 'error_description': '[서버 오류] OAuth 토큰 발급 중 문제가 발생했습니다.'}), 500
    elif grant_type == 'client_credentials':
        try:
            result = oauth_provider_service.client_credentials_token(
                client_id=data.get('client_id', ''),
                client_secret=data.get('client_secret', ''),
                scope=data.get('scope', 'read'),
            )
        except Exception as e:
            current_app.logger.error('OAuth client credentials token failed: %s', e, exc_info=True)
            return jsonify({'error': 'server_error', 'error_description': '[서버 오류] OAuth 토큰 발급 중 문제가 발생했습니다.'}), 500
    else:
        result = {'error': 'unsupported_grant_type', 'error_description': f'지원하지 않는 grant_type: {grant_type}'}

    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@blog_bp.route('/oauth/revoke', methods=['POST'])
def oauth_revoke():
    """OAuth 2.0 토큰 폐기"""
    from services.auth.oauth_provider_service import oauth_provider_service

    data = request.get_json(silent=True) or {}
    token = data.get('token', '')
    if not token:
        return jsonify({'error': 'token이 필요합니다.'}), 400

    try:
        oauth_provider_service.revoke_token(token)
    except Exception as e:
        current_app.logger.error('OAuth revoke failed: %s', e, exc_info=True)
        return jsonify({'error': '[서버 오류] OAuth 토큰 폐기 중 문제가 발생했습니다.'}), 500
    return jsonify({'success': True})


@blog_bp.route('/oauth/clients', methods=['GET'])
def oauth_list_clients():
    """등록된 OAuth 클라이언트 목록"""
    from services.auth.oauth_provider_service import oauth_provider_service
    try:
        clients = oauth_provider_service.list_clients()
    except Exception as e:
        current_app.logger.error('OAuth client list failed: %s', e, exc_info=True)
        return jsonify({'error': '[서버 오류] OAuth 클라이언트 목록 조회 중 문제가 발생했습니다.'}), 500
    return jsonify({'clients': clients})
