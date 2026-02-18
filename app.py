"""
스마트 콘텐츠 생성기 - Flask 애플리케이션 팩토리
"""
import os
import sys
from urllib.parse import urlparse

from flask import Flask, request, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

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

    app.config.from_object('config')
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    import config as config_module
    app.config['STYLE_PROMPTS'] = config_module.STYLE_PROMPTS
    app.config['STYLE_OPTIONS'] = config_module.STYLE_OPTIONS
    app.config['STYLE_MODIFIERS'] = config_module.STYLE_MODIFIERS
    app.config['SUPPORTED_PROVIDERS'] = config_module.SUPPORTED_PROVIDERS

    if test_config:
        app.config.from_mapping(test_config)

    # AI 결과 캐시 초기화
    from services.cache_service import AICacheService
    app.ai_cache = AICacheService(
        db_path=config_module.AI_CACHE_DB,
        ttl_days=config_module.AI_CACHE_TTL_DAYS,
        max_size_mb=config_module.AI_CACHE_MAX_SIZE_MB,
    )

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
            # 헬스체크, 정적 파일은 제외
            if request.path in ('/health', '/api/heartbeat'):
                return None
            # Origin 또는 Referer 헤더 검증
            origin = request.headers.get('Origin')
            referer = request.headers.get('Referer')
            host = request.host_url.rstrip('/')

            def is_local_dev(url):
                """개발 환경의 로컬 주소인지 확인"""
                return app.debug and any(local in url for local in ('localhost', '127.0.0.1'))

            if origin:
                # 'null' origin 허용 제거 (보안 강화)
                if not origin.startswith(host) and origin != 'file://':
                    # 개발 환경에서는 localhost/127.0.0.1 허용
                    if not is_local_dev(origin):
                        return jsonify({'error': 'CSRF 검증 실패: 잘못된 Origin'}), 403
            elif referer:
                parsed = urlparse(referer)
                referer_origin = f"{parsed.scheme}://{parsed.netloc}"
                if not referer_origin.startswith(host):
                    if not is_local_dev(referer_origin):
                        return jsonify({'error': 'CSRF 검증 실패: 잘못된 Referer'}), 403
        return None

    from routes.blog_routes import blog_bp
    from routes.auth_routes import auth_bp
    app.register_blueprint(blog_bp)
    app.register_blueprint(auth_bp)

    return app


app = create_app()

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'true').lower() in ('true', '1', 'yes')  # Temporarily enabled
    port = int(os.getenv('PORT', 5001))
    app.run(debug=debug_mode, port=port)
