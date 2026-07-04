"""통합 서비스 라우트 패키지 — 도메인별 서브모듈 import만으로 자동 등록.

각 서브모듈이 `blog_bp` 데코레이터로 라우트를 등록하므로,
이 패키지를 import하기만 하면 모든 통합 라우트가 활성화된다.

서브모듈:
- imports: Notion, Google Docs, RSS, 북마크, 이메일 임포트
- mcp_plugins: MCP 플러그인/앱/SDK/서버 + 모든 CMS 발행 플러그인
- knowledge: RAG 지식 베이스 (벡터, GraphRAG, 멀티모달)
- content_workspace: 버전 히스토리, 검색, 폴더, 알림, 협업 세션
- automation: Slack/Discord/Telegram 봇, Zapier, Make, IFTTT, Airtable, Sheets, Webhook Relay, Slack/Discord 알림
- misc: OpenAPI, 앱 피드백, OAuth 2.0 공급자
"""
from routes.integrations import (  # noqa: F401 — 부수효과 import (라우트 등록)
    imports,
    mcp_plugins,
    knowledge,
    content_workspace,
    automation,
    misc,
)
