# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 작업 규칙

- 모든 커뮤니케이션은 한국어로 한다
- 전문 용어 사용 시 괄호 안에 한 줄 설명 추가
- 에러 발생 시 "왜 났는지 / 어떻게 고치는지 / 다음에 피하려면" 3단계로 설명

### 안전/보안

- Key/Secret 하드코딩 금지
- 데이터 삭제/교체/마이그레이션은 "경고 + 사용자 확인" 없이 금지

---

## Project Overview

**Insight Engine** - YouTube 영상 URL로 다양한 AI 모델(OpenAI, Claude, Gemini, GLM-4, DeepSeek)을 활용해 고품질 한국어 블로그 포스트를 자동 생성하는 Flask 웹 앱. LiteLLM을 통해 다중 AI 프로바이더를 통합 지원.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행 (개발 모드) → http://localhost:5001
python app.py

# 테스트 실행
pytest tests/ -v

# 단일 테스트 실행
pytest tests/test_routes_smoke.py -v

# 특정 테스트 함수 실행
pytest tests/test_routes_smoke.py::test_home_page -v
```

## Architecture

메인 앱: `스마트 콘텐츠 생성기 20250705(완성)/`

| 파일 | 역할 |
|------|------|
| app.py | Flask 앱 팩토리, 블루프린트 등록 (port 5001) |
| config.py | 토큰 제한, 지원 프로바이더/모델, 스타일 프롬프트 정의 |
| routes/blog_routes.py | API 엔드포인트 (아래 참조) |
| prompts.py | 스타일별 프롬프트 템플릿 정의 |
| services/ai_service.py | LiteLLM `completion()` 호출로 다중 AI 프로바이더 통합 |
| services/content_service.py | YouTube 자막 추출 (Supadata API 우선 → youtube-transcript-api → watch 페이지 폴백) |

### API Endpoints (routes/blog_routes.py)

| 엔드포인트 | 설명 |
|-----------|------|
| `POST /generate` | 단일 URL 콘텐츠 생성 |
| `POST /generate-batch` | 다중 URL 배치 처리 (최대 10개) |
| `POST /regenerate` | 기존 콘텐츠 재생성 |
| `GET /api/providers` | AI 서비스/모델 목록 |
| `POST /api/recommend-style` | YouTube 제목 분석 → 스타일 추천 |
| `POST /api/generate-style` | YouTube 제목+자막 → 맞춤 프롬프트 생성 |

### Request Flow

1. 사용자 URL + API 키 입력 → `/generate` 또는 `/generate-batch`
2. `content_service`가 자막 추출 (Supadata → youtube-transcript-api → watch 페이지 파싱)
3. `content_service.get_top_comments()`로 댓글 수집 (YouTube Data API)
4. `ai_service.create_content()`가 LiteLLM을 통해 선택된 AI 모델 호출
5. JSON 응답 (title, markdown content, html)

### Frontend Architecture (ES6 모듈)

`static/js/main.js` → 모듈 오케스트레이터

| 모듈 | 역할 |
|------|------|
| StorageManager.js | LocalStorage (설정, 히스토리, 커스텀 스타일) |
| ProviderManager.js | AI 서비스/모델 선택, API 키 관리 |
| StyleManager.js | 스타일 선택, 모디파이어, 커스텀 스타일 렌더링 |
| UrlManager.js | URL 입력, 파싱, 다중 URL 관리 |
| ContentGenerator.js | `/generate`, `/generate-batch` API 호출 |
| ReportManager.js | 리포트 카드 생성, 히스토리 로딩, 접기/펼치기 |
| ModalManager.js | 설정 모달, 온보딩, 커스텀 스타일 모달 |
| UIManager.js | 알림(Toast), 로딩 상태, 유틸리티 함수 |

**디자인**: TailwindCSS CDN + 커스텀 테마 (앰버/골드 #D4A574, 다크 모드)

### AI Providers (config.py의 SUPPORTED_PROVIDERS)

| Provider | 모델 예시 |
|----------|----------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o1-mini, o3-mini |
| Anthropic | claude-sonnet-4-20250514, claude-3-5-sonnet, claude-3-haiku |
| Gemini | gemini/gemini-3-flash-preview, gemini/gemini-2.5-flash |
| Zhipu | glm-4, glm-4-flash, glm-4-air |
| DeepSeek | deepseek-chat, deepseek-reasoner |

### Style System (config.py)

**STYLE_PROMPTS** (prompts.py) - 12가지 스타일:
`blog`, `detailed`, `summary`, `easy`, `news`, `script`, `seo`, `needs`, `qna`, `infographic`, `compare`, `sns`

**STYLE_MODIFIERS** - 세부 옵션:
- `length`: short/medium/long (분량 조절)
- `tone`: professional/friendly/humorous (말투)
- `language`: ko/en/ja (출력 언어)
- `emoji`: use/none (이모지 사용 여부)

### YouTube Transcript Handling

`content_service.py` 우선순위 폴백:
1. Supadata API (`supadata_api_key` 제공 시)
2. `youtube-transcript-api` 라이브러리 (지수 백오프 재시도 3회)
3. watch 페이지 직접 파싱 (`_get_transcript_from_watch_page`)

예외 처리: 429 rate limit, IP 차단, 연령 제한, PoToken 필요 등

## API Configuration

`.env.example` 파일을 `.env`로 복사하여 사용. API 키가 설정된 프로바이더만 UI에 표시됨.

```bash
# AI Provider API Keys (최소 하나 필수)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
ZHIPU_API_KEY=...
DEEPSEEK_API_KEY=...

# 선택 사항
SUPADATA_API_KEY=           # YouTube 자막 백업 서비스
YOUTUBE_API_KEY=            # 댓글/제목 조회용
SUPABASE_URL=               # 클라우드 히스토리 저장
SUPABASE_ANON_KEY=          # Supabase Anonymous Key

# 프록시 (YouTube 자막 차단 우회용)
YT_HTTP_PROXY=http://your-proxy:port
YT_HTTPS_PROXY=http://your-proxy:port
```

**사용자 입력 API 키**: 프론트엔드에서 각 요청마다 `apiKey` 파라미터로 전달 (서버 저장 없음)

## Key Patterns

- 모든 API 라우트는 실패 시 JSON `{"error": "메시지"}` 반환
- 배치 처리: `ThreadPoolExecutor` max 5 workers, 최대 10 URL
- `truncate_text()`로 토큰 제한 준수 (MAX_CONTENT_TOKENS: 900,000)
- AI 프롬프트 끝에 한국어 출력 강제: `"결과는 반드시 한국어로 작성해주세요."`
- 클라이언트 하트비트: `/api/heartbeat`, `/api/close` (세션 추적용)
- 사용자 정의 프롬프트: `customPrompt` 파라미터로 스타일 프롬프트 오버라이드 가능

## Testing

주요 테스트 파일:
- `test_routes_smoke.py`: API 라우트 기본 동작
- `test_content_service_transcript_fallback.py`: 자막 폴백 로직
- `test_style_prompts.py`: 스타일 프롬프트 설정
- `test_app_lifecycle_smoke.py`: 앱 생명주기
