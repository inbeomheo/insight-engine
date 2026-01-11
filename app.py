"""
스마트 콘텐츠 생성기 - Flask 애플리케이션 팩토리
"""
import os
import sys

from flask import Flask

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = lambda *args, **kwargs: False


def create_app(test_config=None):
    """Flask 애플리케이션 인스턴스를 생성하고 설정합니다."""
    load_dotenv()

    base_dir = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, 'templates')
    static_dir = os.path.join(base_dir, 'static')

    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=templates_dir,
        static_folder=static_dir,
    )

    app.config.from_object('config')

    import config as config_module
    app.config['STYLE_PROMPTS'] = config_module.STYLE_PROMPTS
    app.config['STYLE_OPTIONS'] = config_module.STYLE_OPTIONS
    app.config['STYLE_MODIFIERS'] = config_module.STYLE_MODIFIERS
    app.config['SUPPORTED_PROVIDERS'] = config_module.SUPPORTED_PROVIDERS

    if test_config:
        app.config.from_mapping(test_config)

    from routes.blog_routes import blog_bp
    from routes.auth_routes import auth_bp
    app.register_blueprint(blog_bp)
    app.register_blueprint(auth_bp)

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
