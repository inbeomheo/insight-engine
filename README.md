# Insight Engine - AI 콘텐츠 분석 도구

YouTube 영상 URL을 입력하면 다양한 AI 모델(OpenAI, Claude, Gemini, GLM-4, DeepSeek)을 활용하여 고품질 한국어 콘텐츠를 자동으로 생성하는 웹 애플리케이션입니다.

## 주요 기능

- **다중 AI 프로바이더 지원**: OpenAI, Anthropic Claude, Google Gemini, Zhipu GLM, DeepSeek
- **12가지 출력 스타일**: 블로그, 요약, 상세분석, 뉴스, 스크립트, Q&A, 인포그래픽 등
- **배치 처리**: 최대 10개 URL을 한 번에 분석
- **커스텀 스타일**: 나만의 프롬프트로 분석 스타일 생성
- **마인드맵 시각화**: 분석 결과를 마인드맵으로 표시
- **실시간 스트리밍**: 분석 결과를 실시간으로 표시

---

## 빠른 시작

### 1. 필수 요구사항
- Python 3.8 이상
- AI Provider API 키 (최소 하나 필수)

### 2. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd "스마트 콘텐츠 생성기 20250705(완성)"

# 가상환경 생성 (권장)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env.example` 파일을 `.env`로 복사하고 API 키를 설정합니다:

```bash
cp .env.example .env
```

`.env` 파일 예시:
```env
# AI Provider API Keys (최소 하나 필수)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...

# 선택 사항
SUPADATA_API_KEY=            # 자막 백업 서비스
YOUTUBE_API_KEY=             # 댓글 수집용
```

> **중요**: API 키가 설정된 프로바이더만 UI에 표시됩니다.

### 4. 실행

```bash
python app.py
```

브라우저에서 http://localhost:5001 접속

---

## 환경변수 상세 설명

### AI Provider API Keys (최소 하나 필수)

| 환경변수 | 설명 | 발급처 |
|---------|------|-------|
| `OPENAI_API_KEY` | OpenAI API 키 (GPT-4o, GPT-4 Turbo 등) | [platform.openai.com](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | Anthropic API 키 (Claude Sonnet, Haiku 등) | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| `GEMINI_API_KEY` | Google Gemini API 키 | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `ZHIPU_API_KEY` | Zhipu AI API 키 (GLM-4 등) | [open.bigmodel.cn](https://open.bigmodel.cn/usercenter/apikeys) |
| `DEEPSEEK_API_KEY` | DeepSeek API 키 | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |

### 선택 환경변수

| 환경변수 | 설명 | 발급처 |
|---------|------|-------|
| `SUPADATA_API_KEY` | YouTube 자막 백업 서비스 | [supadata.ai](https://supadata.ai/) |
| `YOUTUBE_API_KEY` | YouTube 댓글 수집용 | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `SUPABASE_URL` | Supabase 프로젝트 URL | [Supabase Dashboard](https://supabase.com/) |
| `SUPABASE_ANON_KEY` | Supabase Anonymous Key | Supabase Dashboard > Settings > API |

### 프록시 설정 (선택)

YouTube 자막 수집이 차단되는 환경에서 사용:

```env
YT_HTTP_PROXY=http://your-proxy:port
YT_HTTPS_PROXY=http://your-proxy:port
```

---

## 프로젝트 구조

```
insight-engine/
├── app.py                      # Flask 앱 진입점 (포트 5001)
├── config.py                   # 환경변수 로딩, 프로바이더 설정
├── prompts.py                  # 스타일별 프롬프트 템플릿
├── requirements.txt            # Python 의존성
├── .env.example                # 환경변수 템플릿
│
├── routes/
│   └── blog_routes.py          # API 엔드포인트
│
├── services/
│   ├── ai_service.py           # LiteLLM 기반 AI 호출
│   └── content_service.py      # YouTube 자막/댓글 추출
│
├── static/js/
│   ├── main.js                 # 프론트엔드 진입점
│   └── modules/
│       ├── StorageManager.js   # LocalStorage 관리
│       ├── ProviderManager.js  # AI 서비스 선택
│       ├── StyleManager.js     # 스타일 선택
│       ├── ContentGenerator.js # API 호출
│       ├── ReportManager.js    # 결과 카드 표시
│       ├── ModalManager.js     # 모달 관리
│       └── UIManager.js        # UI 유틸리티
│
└── templates/
    └── index.html              # 메인 HTML
```

---

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/generate` | POST | 단일 URL 콘텐츠 생성 |
| `/generate-batch` | POST | 다중 URL 배치 처리 (최대 10개) |
| `/regenerate` | POST | 기존 콘텐츠 재생성 |
| `/api/providers` | GET | 사용 가능한 AI 서비스 목록 |
| `/api/recommend-style` | POST | AI 스타일 추천 |
| `/api/generate-style` | POST | 맞춤 프롬프트 생성 |

---

## 지원 AI 모델

### OpenAI
- gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o1-mini, o3-mini

### Anthropic Claude
- claude-sonnet-4-20250514, claude-3-5-sonnet, claude-3-haiku

### Google Gemini
- gemini-3-flash-preview, gemini-2.5-flash, gemini-2.0-flash

### Zhipu AI
- glm-4, glm-4-flash, glm-4-air

### DeepSeek
- deepseek-chat, deepseek-reasoner

---

## 배포

### Railway

1. GitHub 저장소 연결
2. Variables 탭에서 환경변수 설정
3. 자동 배포

### 수동 배포

```bash
# 프로덕션 모드
export FLASK_ENV=production
export FLASK_DEBUG=0
python app.py
```

---

## 테스트

```bash
# 전체 테스트
pytest tests/ -v

# 특정 테스트
pytest tests/test_routes_smoke.py -v
```

---

## 문제 해결

### AI 서비스가 표시되지 않음
- `.env` 파일에 해당 프로바이더의 API 키가 설정되어 있는지 확인
- API 키가 유효한지 확인

### YouTube 자막 수집 실패
- `SUPADATA_API_KEY`를 설정하여 백업 서비스 사용
- 프록시 설정 (`YT_HTTP_PROXY`, `YT_HTTPS_PROXY`)

### 댓글이 수집되지 않음
- `YOUTUBE_API_KEY`가 설정되어 있는지 확인
- YouTube Data API v3가 활성화되어 있는지 확인

---

## 보안 주의사항

- **API 키는 절대 공개 저장소에 커밋하지 마세요**
- `.env` 파일은 `.gitignore`에 포함되어 있습니다
- 프로덕션 환경에서는 환경변수로 직접 설정하세요

---

## 라이선스

MIT License
