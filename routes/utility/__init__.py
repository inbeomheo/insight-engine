"""utility 서브 라우트 패키지 — utility_routes.py에서 분리된 모듈들.

서브모듈:
- operations: 헬스/heartbeat/close/providers/ollama (8개 엔드포인트)
- feedback_quality: 캐시/피드백/팩트체크/SEO/표절/가독성/감정/NPS (9개)
- generation: AI 스타일 추천/생성 (2개)
- external: 웹훅/재생목록/추천소스/워드클라우드/스키마/RSS (6개)
- content_evaluation: 콘텐츠 종합 평가 (등급/헤드라인/퀴즈/CTA 등)
- text_structure: 문장/단락/연결어/구조 분석
- text_quality: 표현 품질 (군더더기/어휘/톤/클리셰)
- seo_aeo: SEO/AEO/EEAT/구조화 데이터
- content_meta: 콘텐츠 메타데이터 (페르소나/브랜드/투명성/위험)
"""
from routes.utility import (  # noqa: F401 — 부수효과 import
    content_evaluation,
    content_meta,
    external,
    feedback_quality,
    generation,
    operations,
    seo_aeo,
    text_quality,
    text_structure,
)
