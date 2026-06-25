"""
스마트 콘텐츠 생성기 - Flask 애플리케이션 팩토리
"""
import os
import sys
from urllib.parse import urlparse

from flask import Flask, request, jsonify
from utils.responses import api_error
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from utils.production_readiness import (
    default_content_security_policy,
    parse_cors_origins,
    validate_production_security_config,
)

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = lambda *args, **kwargs: False


def create_app(test_config=None):
    """Flask 애플리케이션 인스턴스를 생성하고 설정합니다."""
    load_dotenv()

    base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=None,  # 프론트엔드는 Next.js에서 제공
    )

    # 프록시 환경(Railway, Render 등)에서 올바른 host/scheme 인식
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # CORS: 프론트엔드(Next.js)에서 Flask를 직접 호출할 수 있도록 허용
    allowed_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3001').split(',')

    # 부팅 시 production 보안 설정 검증 (fail-closed)
    # FLASK_ENV != 'production'이면 검증을 건너뛰므로 개발/테스트 환경에는 영향 없음
    flask_env = os.getenv('FLASK_ENV', '')
    _csp_header = os.getenv('CONTENT_SECURITY_POLICY') or default_content_security_policy(flask_env)
    validate_production_security_config(
        flask_env,
        parse_cors_origins(os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3001')),
        os.getenv('METRICS_AUTH_TOKEN', ''),
        os.getenv('ENCRYPTION_SECRET', ''),
        _csp_header,
    )

    CORS(app, origins=[o.strip() for o in allowed_origins], supports_credentials=True)

    app.config.from_object('config')
    # /api/providers 등 순서가 UI 기본 선택에 영향을 주므로 JSON 키 정렬을 끈다.
    app.json.sort_keys = False
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    # 요청 본문 최대 크기 제한 (2MB) — 대용량 입력 DoS 방어
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

    # Rate Limiter 초기화
    from extensions import limiter
    limiter.init_app(app)

    import config as config_module
    app.config['STYLE_PROMPTS'] = config_module.STYLE_PROMPTS
    app.config['STYLE_OPTIONS'] = config_module.STYLE_OPTIONS
    app.config['STYLE_MODIFIERS'] = config_module.STYLE_MODIFIERS
    app.config['SUPPORTED_PROVIDERS'] = config_module.SUPPORTED_PROVIDERS

    if test_config:
        app.config.from_mapping(test_config)

    # AI 결과 캐시 초기화
    from services.core.cache_service import AICacheService
    app.ai_cache = AICacheService(
        db_path=config_module.AI_CACHE_DB,
        ttl_days=config_module.AI_CACHE_TTL_DAYS,
        max_size_mb=config_module.AI_CACHE_MAX_SIZE_MB,
    )

    # API 응답 시간 로깅
    import time as _time
    import logging as _logging
    _perf_logger = _logging.getLogger('api.perf')

    @app.before_request
    def _start_timer():
        request._start_time = _time.perf_counter()

    # Issue #17 소PR B-2: g.auth 슬롯 초기화 (UserAccount Aggregate는 require_auth가 채움)
    from src.contexts.identity.interface.auth_decorators import inject_auth_context
    app.before_request(inject_auth_context)

    @app.after_request
    def _log_response_time(response):
        start = getattr(request, '_start_time', None)
        if start is not None:
            elapsed_ms = (_time.perf_counter() - start) * 1000
            response.headers['X-Response-Time'] = f'{elapsed_ms:.1f}ms'
            if elapsed_ms > 1000:  # 1초 이상은 warning
                _perf_logger.warning('느린 응답: %s %s %.1fms', request.method, request.path, elapsed_ms)
        return response

    # 보안 헤더 설정
    @app.after_request
    def add_security_headers(response):
        """보안 헤더를 응답에 추가합니다."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # HTTPS 환경에서만 HSTS 활성화
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # CSRF 보호 (Origin 헤더 검증)
    @app.before_request
    def csrf_protect():
        """POST/PUT/DELETE 요청에 대해 Origin 헤더를 검증합니다."""
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            # 테스트 환경에서는 CSRF 건너뜀
            if app.testing:
                return None
            # 헬스체크, 정적 파일은 제외
            if request.path in ('/health', '/api/heartbeat'):
                return None
            # Origin 또는 Referer 헤더 검증
            origin = request.headers.get('Origin')
            referer = request.headers.get('Referer')
            host = request.host_url.rstrip('/')

            def is_allowed_origin(url):
                """CORS 허용 목록에 포함된 origin인지 확인"""
                return url.rstrip('/') in [o.rstrip('/') for o in allowed_origins]

            if origin:
                if not origin.startswith(host) and origin != 'file://':
                    # CORS 허용 목록 또는 로컬 개발 환경이면 통과
                    if not is_allowed_origin(origin):
                        return api_error('CSRF 검증 실패: 잘못된 Origin', 403)
            elif referer:
                parsed = urlparse(referer)
                referer_origin = f"{parsed.scheme}://{parsed.netloc}"
                if not referer_origin.startswith(host):
                    if not is_allowed_origin(referer_origin):
                        return api_error('CSRF 검증 실패: 잘못된 Referer', 403)
            else:
                # Origin/Referer 모두 없는 경우: API 키 인증이 있으면 허용 (프로그래밍 방식 접근)
                if request.headers.get('X-API-Key') or request.headers.get('Authorization'):
                    return None
                return api_error('CSRF 검증 실패: Origin 또는 Referer 헤더가 필요합니다.', 403)
        return None

    # 글로벌 에러 핸들러 — JSON 응답 통일
    @app.errorhandler(404)
    def not_found(e):
        return api_error('요청한 페이지를 찾을 수 없습니다.', 404)

    @app.errorhandler(405)
    def method_not_allowed(e):
        return api_error('허용되지 않는 요청 메서드입니다.', 405)

    @app.errorhandler(413)
    def payload_too_large(e):
        return api_error('요청 데이터가 너무 큽니다.', 413)

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.error(f'Unhandled 500: {e}')
        return api_error('[서버 오류] 처리 중 예상치 못한 오류가 발생했습니다. 다시 시도해주세요.', 500)

    from routes.blog_routes import blog_bp
    from routes.auth_routes import auth_bp
    # 분리된 라우트 모듈 import → blog_bp에 라우트 등록
    import routes.utility_routes      # noqa: F401
    import routes.advanced_routes     # noqa: F401
    import routes.export_routes       # noqa: F401
    import routes.integration_routes  # noqa: F401
    import routes.payment_routes      # noqa: F401
    import routes.video_deepdive_routes  # noqa: F401
    app.register_blueprint(blog_bp)
    app.register_blueprint(auth_bp)

    from routes.marketplace_routes import marketplace_bp
    app.register_blueprint(marketplace_bp)

    # Phase 8: 콘텐츠 관리 & 라이브러리 라우트
    from routes.content_mgmt_routes import content_mgmt_bp
    app.register_blueprint(content_mgmt_bp)

    # Phase 7: GraphQL API (F7-09)
    from routes.graphql_routes import graphql_bp
    app.register_blueprint(graphql_bp)

    # NotebookLM 연동 라우트
    from routes.notebooklm_routes import notebooklm_bp
    app.register_blueprint(notebooklm_bp)

    # 제품 지원/피드백 챗봇 라우트
    from routes.support_routes import support_bp
    app.register_blueprint(support_bp)

    # 에이전트 오케스트레이션 라우트
    from routes.agent_routes import agent_bp
    app.register_blueprint(agent_bp)

    # 에이전트 도구 디스커버리 (AGENT_MODE_ENABLED=true 시)
    import config as _cfg
    if getattr(_cfg, 'AGENT_MODE_ENABLED', False):
        with app.app_context():
            try:
                from agent.tools import discover_tools
                discover_tools()
                app.logger.info('에이전트 도구 디스커버리 완료')
            except Exception as e:
                app.logger.warning('에이전트 도구 디스커버리 실패 (무시): %s', e)

    # 예약 발행 스케줄러 시작
    from services.data.scheduler_worker import start_scheduler
    start_scheduler(app)

    return app


app = create_app()

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() in ('true', '1', 'yes')
    port = int(os.getenv('PORT', 5001))
    app.run(debug=debug_mode, port=port, threaded=True)
