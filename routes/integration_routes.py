"""
통합 서비스 라우트 (얇은 진입 shim).

실제 라우트 정의는 routes/integrations/ 서브패키지에 도메인별로 분리되어 있다.
app.py에서 `import routes.integration_routes`만 호출하면 부수효과로 모든 통합 라우트가
등록된다.

도메인별 모듈:
- mcp_plugins: MCP 플러그인/앱/SDK/서버 + CMS 발행 플러그인
- knowledge: RAG 지식 베이스 (벡터, GraphRAG, 멀티모달)
- misc: 앱 피드백
"""
from routes import integrations  # noqa: F401 — 부수효과 import (라우트 등록)
