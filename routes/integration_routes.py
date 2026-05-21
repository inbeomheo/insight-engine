"""
통합 서비스 라우트 (얇은 진입 shim).

실제 라우트 정의는 routes/integrations/ 서브패키지에 도메인별로 분리되어 있다.
app.py에서 `import routes.integration_routes`만 호출하면 부수효과로 모든 통합 라우트가
등록된다.

도메인별 모듈:
- imports: Notion, Google Docs, RSS, 북마크, 이메일 임포트
- mcp_plugins: MCP 플러그인/앱/SDK/서버 + CMS 발행 플러그인
- workflow: 발행 큐, 예약 발행, CMS 통합 허브
- knowledge: RAG 지식 베이스 (벡터, GraphRAG, 멀티모달)
- content_workspace: 버전 히스토리, 검색, 폴더, 알림, 협업 세션
- automation: Slack/Discord/Telegram 봇, Zapier, Make, IFTTT, Airtable, Sheets, Webhook Relay, Slack/Discord 알림
- misc: OpenAPI, 앱 피드백, OAuth 2.0 공급자
"""
from routes import integrations  # noqa: F401 — 부수효과 import (라우트 등록)
