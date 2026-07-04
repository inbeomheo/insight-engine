"""blog 부가 라우트 패키지 — blog_routes.py에서 분리된 모듈들.

각 서브모듈이 blog_bp 데코레이터로 라우트를 등록하므로,
이 패키지를 import하기만 하면 모든 라우트가 활성화된다.

서브모듈:
- templates: 프롬프트 템플릿 갤러리 API (5개 엔드포인트)
"""
from routes.blog import (  # noqa: F401 — 부수효과 import (라우트 등록)
    templates,
)
