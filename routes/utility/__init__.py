"""utility 서브 라우트 패키지 — utility_routes.py에서 분리된 모듈들.

서브모듈:
- operations: 헬스/heartbeat/close/providers/ollama (8개 엔드포인트)
- feedback_quality: 캐시/피드백/팩트체크/SEO/표절/가독성/감정/NPS (9개)
- external: 웹훅/재생목록/추천소스/워드클라우드/스키마/RSS (6개)
"""
from routes.utility import (  # noqa: F401 — 부수효과 import
    external,
    feedback_quality,
    operations,
)
