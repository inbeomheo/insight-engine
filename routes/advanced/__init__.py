"""고급 생성 라우트 서브패키지 — advanced_routes.py에서 분리된 모듈들.

각 서브모듈이 blog_bp 데코레이터로 라우트를 등록하므로,
이 패키지를 import하기만 하면 모든 라우트가 활성화된다.

서브모듈:
- mindmap: 콘텐츠 → 마인드맵 변환 (1개 엔드포인트)
- fusion: N개 URL → 1편 융합 (1개 엔드포인트)

멀티스타일/캠페인/파이프라인/에이전트/메모리/미디어 등은 routes/advanced_routes.py에
그대로 유지 (test patch 호환성 보존).
"""
from routes.advanced import (  # noqa: F401 — 부수효과 import (라우트 등록)
    fusion,
    mindmap,
)
