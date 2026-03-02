# Findings — TOP 20 기능 구현

## 출처

- Feature Scout 보고서: `docs/feature-scout-max-loop-2026-03-02.md`
- 원본 46개 → 임팩트/난이도/아키텍처 적합성 기준 20개 선별

## 프로젝트 아키텍처 분석 (2026-03-02)

### 백엔드 현황

- **API 엔드포인트**: ~80개 (blog_bp 50+ / auth_bp 30+)
- **서비스 파일**: 40+개 (RAG 7개, 에이전트 5개, MCP 6개 포함)
- **프롬프트**: 14개 UI 스타일 + 2개 내부 전용 (mindmap, comment_summary)
- **프로바이더**: 4개 (Zhipu, DeepSeek, Ollama, OpenRouter)
- **모디파이어**: 3개 (length, writing_style, language)
- **이미 구현된 고급 기능**: TTS, Whisper, RAG/GraphRAG/CRAG, 에이전트 오케스트레이터, 웹 검색 보강, 캐시, 파이프라인

### 프론트엔드 현황

- **프레임워크**: Next.js 16 + Tailwind v4 + shadcn
- **상태 관리**: Zustand stores
- **훅**: 12개 (useGenerate, usePipeline, useSchedule 등)
- **컴포넌트**: ~60개 (input 3, result 12, modals 6, settings 5, ui 20+)
- **API 클라이언트**: `frontend/lib/api.ts` — fetch 기반, 타임아웃별 설정

### 기존 인프라 활용 가능 지점

| 신규 기능 | 활용 가능 기존 코드 |
|-----------|------------------|
| F01 상세도 프리셋 | `config.py` LENGTH_MAX_TOKENS / STYLE_TEMPERATURE 패턴 |
| F03 스니펫 | `auth_routes.py`의 user/styles CRUD 패턴 동일 |
| F04 자막 토글 | `content_service.py`가 이미 자막 세그먼트 보유 |
| F06 챕터 | `event_extraction_service.py` 타임라인 추출 패턴 참고 |
| F08 채널 모니터 | `scheduler_worker.py` APScheduler 잡 등록 패턴 |
| F09 인라인 편집 | `mcp/apps/inline_editor.py` 이미 존재 (MCP 앱) |
| F12 패키지 출력 | `export_service.py` DOCX 패턴 확장 |
| F14 승인 플로우 | `workspace_service.py` 역할 체계 기반 |
| F17 발행 큐 | `webhook_service.py` fire-and-forget 패턴 + 재시도 |
| F19 인용 | `seo_metadata_service.py` 메타데이터 추출 패턴 |
| F20 캠페인 팩 | `advanced_routes.py` generate-multi 엔드포인트 |

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| chapter_service는 별도 AI 호출 | 메인 생성과 분리해야 프롬프트 오버헤드 없음 |
| QA 게이트는 규칙 기반 + AI 기반 혼합 | regex만으로는 팩트 체크 불가, AI만으로는 비용 과다 |
| 발행 큐는 SQLite (로컬) + Supabase (클라우드) 이중 지원 | 비인증 사용자도 큐 사용 가능하게 |
| InlineEditor는 프론트엔드 Selection API 기반 | ContentEditable보다 안전 |

## Resources

- Flask 앱: `app.py` (팩토리 패턴, 2개 Blueprint)
- Next.js 프록시: `frontend/next.config.ts` (rewrites → localhost:5001)
- 타입 정의: `frontend/lib/types.ts`
- API 클라이언트: `frontend/lib/api.ts`
- Zustand 스토어: `frontend/stores/`

---

*Update this file after every 2 view/browser/search operations*
