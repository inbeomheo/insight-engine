# Insight Engine 코드 문제점 분석 보고서

> 분석일: 2026-04-07 | 총 41건 (Critical 6 / High 16 / Medium 10 / Low 9)

---

## Critical (치명적) — 6건

### C-1. XSS — CompareManager 에러 메시지 비새니타이징
- **파일**: `static/js/modules/CompareManager.js:134`
- **문제**: `catch (e)` 블록에서 `e.message`를 `innerHTML`에 새니타이징 없이 삽입. 서버 응답에 악성 HTML이 포함되면 실행됨.
- **수정 방향**: `this.ui.escapeHtml(e.message)` 사용

### C-2. XSS — CompareManager result.error 비새니타이징
- **파일**: `static/js/modules/CompareManager.js:189`
- **문제**: `result.error`를 `escapeHtml()` 없이 `innerHTML`에 직접 삽입. 같은 파일 198행의 `result.title`은 보호하면서 오류 메시지는 누락.
- **수정 방향**: `this.ui.escapeHtml(result.error)` 사용

### C-3. 인증 없는 캐시 전체 삭제 엔드포인트
- **파일**: `routes/utility_routes.py:280`
- **문제**: `DELETE /api/cache`에 `@require_auth` 데코레이터 없음. 동일 기능인 `/api/cache/ai`(라인 655)는 인증 적용되어 있음. 누구든 캐시 전체 삭제 가능.
- **수정 방향**: `@require_auth` 데코레이터 추가

### C-4. SSRF — Ollama 검증 시 사용자 입력 URL로 HTTP 요청
- **파일**: `routes/utility_routes.py:232-242`
- **문제**: `POST /api/providers/validate`에서 Ollama 검증 시 `api_key` 값을 `base_url`로 그대로 사용하여 `requests.get(f'{base_url}/api/tags')` 호출. 내부 네트워크/AWS 메타데이터 접근 가능.
- **수정 방향**: URL 허용 목록 검증 또는 프라이빗 IP 차단 로직 추가

### C-5. Docker frontend 서비스가 백엔드 이미지 사용
- **파일**: `docker-compose.yml:50-53`
- **문제**: `frontend` 서비스가 `target: final`(백엔드 이미지)을 사용. Next.js 컨테이너가 백엔드 이미지에서 실행되어 시작 실패.
- **수정 방향**: `target: frontend-builder` 또는 별도 프론트엔드 스테이지 지정

### C-6. nginx.conf 파일 누락
- **파일**: `docker-compose.yml:96`
- **문제**: Nginx 서비스가 `./nginx.conf`를 마운트하지만 해당 파일이 저장소에 없음. `docker-compose up` 시 Nginx 시작 불가.
- **수정 방향**: `nginx.conf` 파일 생성 또는 docker-compose에서 제거

---

## High (높음) — 16건

### H-1. Supabase 비활성화 시 전체 인증 우회
- **파일**: `services/data/supabase_service.py:179-181`
- **문제**: `is_supabase_enabled()`가 False이면 `g.user_id = None`으로 설정하고 인증 없이 통과. 환경변수 미설정 시 모든 인증 보호 무력화.
- **수정 방향**: Supabase 비활성화 시에도 최소한의 인증 체크 또는 경고 로그 추가

### H-2. API 키 평문 저장 (암호화 폴백)
- **파일**: `services/data/supabase_service.py:106-113`
- **문제**: `ENCRYPTION_SECRET` 미설정 시 API 키를 평문으로 DB에 저장. 사용자의 외부 API 키가 그대로 노출됨.
- **수정 방향**: 암호화 키 미설정 시 에러 발생시키거나 API 키 저장 자체를 거부

### H-3. 비밀번호 변경 시 현재 비밀번호 미검증
- **파일**: `routes/auth_routes.py:520-536`
- **문제**: `PUT /api/user/password`에서 `new_password`만 받고 현재 비밀번호 확인 없이 변경. JWT 탈취 시 계정 완전 탈취.
- **수정 방향**: `current_password` 필드 추가 및 검증 로직 구현

### H-4. is_admin() 이메일 폴백 컬럼 오류
- **파일**: `services/data/supabase_service.py:681-688`
- **문제**: 이메일로 2차 admin 조회 시 `.eq('user_id', user_email)`로 잘못된 컬럼 사용. 의도치 않은 권한 상승 또는 정당한 관리자 누락.
- **수정 방향**: `.eq('email', user_email)` 또는 별도 이메일 컬럼 사용

### H-5. ENCRYPTION_KEY vs ENCRYPTION_SECRET 환경변수명 불일치
- **파일**: `config.py:529` / `.env.example:64`
- **문제**: `config.py`는 `ENCRYPTION_KEY`를 읽고, `.env.example`은 `ENCRYPTION_SECRET`으로 안내. 운영자가 가이드를 따라도 암호화 미작동.
- **수정 방향**: 한쪽으로 통일 (config.py 또는 .env.example 수정)

### H-6. ZHIPUAI_API_KEY vs ZAI_API_KEY 불일치
- **파일**: `config.py:34` / `.env.example:24`
- **문제**: `config.py`는 `ZHIPUAI_API_KEY`를 읽지만 LiteLLM은 `ZAI_API_KEY` 사용. 키가 있어도 프로바이더 누락.
- **수정 방향**: LiteLLM 호환 환경변수명으로 통일

### H-7. GLM 재시도 for...else 구조 버그
- **파일**: `services/core/ai_service.py:399-418`
- **문제**: `for...else`에서 `raise`가 호출되면 `else` 블록 도달 불가 (데드 코드). 마지막 시도 실패 시 `response` 미정의로 `NameError` 크래시.
- **수정 방향**: 루프 후 명시적 에러 처리 추가, else 블록 제거

### H-8. _providers_cache 전역 캐시 스레드 안전 미보장
- **파일**: `config.py:280-297`
- **문제**: `_providers_cache`와 `_providers_cache_time` 갱신에 락 없음. `threaded=True` 환경에서 동시 쓰기 레이스 컨디션.
- **수정 방향**: `threading.Lock()` 추가

### H-9. Notion/Google Docs import에서 클라이언트 API 키 수락
- **파일**: `routes/integration_routes.py:50`
- **문제**: 요청 본문의 `api_key`를 그대로 사용하여 외부 API 호출. 서버를 프록시로 악용해 타인의 워크스페이스 접근 가능.
- **수정 방향**: 서버 측 환경변수의 API 키만 사용하도록 변경

### H-10. ResultCard setInterval 폴링 cleanup 없음
- **파일**: `frontend/components/result/ResultCard.tsx:259`
- **문제**: `handleNotebookLm` 내 `setInterval` 폴링이 컴포넌트 언마운트 시 `clearInterval` 없음. 메모리 누수 및 불필요한 API 요청.
- **수정 방향**: `useEffect` cleanup 또는 `useRef`로 interval ID 관리 후 정리

### H-11. useKeyboardShortcuts 이벤트 리스너 무한 재등록
- **파일**: `frontend/hooks/useKeyboardShortcuts.ts:57`
- **문제**: `useEffect` 의존성의 `shortcuts`가 매 렌더마다 새 배열 참조. 리스너 제거/재등록 반복.
- **수정 방향**: `useMemo`로 `shortcuts` 안정화

### H-12. 스트리밍 요청 타임아웃 미적용
- **파일**: `frontend/lib/api.ts:47-57`
- **문제**: `generateStream`과 `runPipeline`이 `request()` 헬퍼를 우회하여 raw `fetch` 사용. `TIMEOUT_MS` 미적용으로 무한 대기 가능.
- **수정 방향**: `AbortSignal.timeout()` 적용

### H-13. nixpacks.toml에 ffmpeg 누락
- **파일**: `nixpacks.toml:5`
- **문제**: `nixPkgs`에 `ffmpeg` 없음. Railway 배포에서 yt-dlp, faster-whisper 전체 실패.
- **수정 방향**: `nixPkgs`에 `ffmpeg` 추가

### H-14. pytest-timeout이 requirements.txt에 없음
- **파일**: `requirements.txt` / `.github/workflows/ci.yml:55`
- **문제**: CI에서 `--timeout=60` 사용하지만 `pytest-timeout` 패키지가 의존성에 없음.
- **수정 방향**: `requirements.txt`에 `pytest-timeout` 추가

### H-15. 라우트 통합 테스트 전무
- **파일**: `routes/` (11개 파일)
- **문제**: auth_routes, payment_routes, export_routes 등 핵심 라우트에 대응하는 HTTP 레벨 통합 테스트가 없음.
- **수정 방향**: Flask test client 기반 통합 테스트 추가

### H-16. POST /api/fact-check 인증 없음
- **파일**: `routes/utility_routes.py:698-708`
- **문제**: AI 비용이 발생하는 팩트체크 엔드포인트에 `@require_auth` 없음. rate limit도 없음.
- **수정 방향**: `@require_auth` + `@require_usage` 데코레이터 추가

---

## Medium (중간) — 10건

### M-1. per_page 파라미터 상한 미검증
- **파일**: `routes/auth_routes.py:412-413`, `620-621`
- **문제**: `per_page` 쿼리 파라미터에 상한 없음. `per_page=1000000` 요청 시 DB 과부하.
- **수정 방향**: `min(per_page, 100)` 등 상한 적용

### M-2. custom_prompt 프롬프트 인젝션 미필터링
- **파일**: `routes/blog_routes.py:203-216`
- **문제**: 2000자 길이 제한만 있고 "이전 지시를 무시하고..." 류의 인젝션 패턴 필터링 없음.
- **수정 방향**: 금지 패턴 필터 또는 별도 user message로 분리

### M-3. create_content_stream() RAG/메모리 컨텍스트 누락
- **파일**: `services/core/ai_service.py:477`
- **문제**: 스트리밍 함수에서 `rag_context`, `web_context`, `memory_context`를 주입하지 않음. 일반 생성 대비 품질 저하.
- **수정 방향**: `create_content()`와 동일한 컨텍스트 빌드 로직 적용

### M-4. InlineEditor 취소 시 이벤트 리스너 누수
- **파일**: `static/js/modules/report/InlineEditor.js:101-104`
- **문제**: `body.innerHTML = originalHtml`로 DOM 복원 시 이벤트 리스너 미정리.
- **수정 방향**: 복원 전 리스너 명시적 제거

### M-5. VideoSelectionModal ARIA 속성 전무
- **파일**: `static/js/modules/VideoSelectionModal.js:18-65`
- **문제**: `role="dialog"`, `aria-modal`, `aria-labelledby` 없음. 포커스 트랩 미구현.
- **수정 방향**: ARIA 속성 및 포커스 트랩 추가

### M-6. CollaborativeEditor 폴링 stale closure
- **파일**: `frontend/components/editor/CollaborativeEditor.tsx:97`
- **문제**: `useEffect` 의존성에 `version` 포함. 변경마다 interval 재생성, 타이밍에 따라 heartbeat 누락 또는 중복.
- **수정 방향**: `useRef`로 version 참조하거나 의존성 안정화

### M-7. optional_auth 만료 토큰 무음 처리
- **파일**: `services/data/supabase_service.py:207`
- **문제**: `_validate_token()` 실패 시 경고 로그 없이 `user_id=None`으로 익명 처리.
- **수정 방향**: 실패 시 `logger.warning()` 추가

### M-8. config.py __all__ 이후 변수 선언
- **파일**: `config.py:509-519` (\_\_all\_\_), `525-582` (변수 정의)
- **문제**: `__all__`에 열거된 변수가 그 이후에 정의됨. `from config import *` 시 NameError 가능.
- **수정 방향**: `__all__`을 파일 끝으로 이동

### M-9. K8s PVC ReadWriteOnce + replicas 2
- **파일**: `k8s/deployment.yaml:219`
- **문제**: `ReadWriteOnce` PVC인데 `replicas: 2`. 두 번째 Pod가 볼륨 마운트 불가로 Pending.
- **수정 방향**: `ReadWriteMany`로 변경하거나 replicas 1로 조정

### M-10. CI 테스트 2회 중복 실행
- **파일**: `.github/workflows/ci.yml:64-69`
- **문제**: 단위 테스트 + 커버리지 단계에서 전체 테스트를 2번 실행. CI 시간 2배.
- **수정 방향**: 단일 실행에 `--cov` 플래그 통합

---

## Low (낮음) — 9건

### L-1. 웹훅 test() SSRF 검증 누락
- **파일**: `services/platform/webhook_service.py:135-149`
- **문제**: `test()` 메서드에서 `_validate_webhook_url` 호출 없이 직접 POST 요청.
- **수정 방향**: `test()`에도 URL 검증 적용

### L-2. _escapeHtml 중복 정의
- **파일**: `static/js/modules/PresetManager.js:146-150`, `static/js/modules/report/InlineEditor.js:153-157`
- **문제**: 동일 로직이 두 클래스에 중복 정의.
- **수정 방향**: 공유 유틸리티로 추출

### L-3. ResultCard.tsx updated 변수 미사용
- **파일**: `frontend/components/result/ResultCard.tsx:264-266`
- **문제**: `updated` 변수 생성 후 미참조. 데드 코드.
- **수정 방향**: 제거

### L-4. Procfile vs nixpacks.toml worker 수 불일치
- **파일**: `Procfile`, `nixpacks.toml`
- **문제**: `--workers 1 --threads 2` vs `--workers 2 --threads 4`. 어느 것이 사용되는지 불명확.
- **수정 방향**: 하나로 통일

### L-5. scrapling 버전 미고정
- **파일**: `requirements.txt:23`
- **문제**: 버전 지정 없이 선언. 빌드 재현성 저하.
- **수정 방향**: 버전 핀 추가

### L-6. 프론트엔드 단위 테스트 전무
- **파일**: `frontend/package.json`
- **문제**: jest/vitest 등 테스트 러너 없음. React 컴포넌트 자동화 테스트 부재.
- **수정 방향**: vitest + React Testing Library 도입

### L-7. 비밀번호 최소 길이 6자
- **파일**: `routes/auth_routes.py:96`
- **문제**: NIST SP 800-63B 권고(8자) 미달.
- **수정 방향**: 최소 8자로 상향

### L-8. 타임스탬프 포매팅 예외 무음 처리
- **파일**: `services/core/ai_service.py:111-112`
- **문제**: `except Exception: return ""` — 로깅 없이 무음 실패.
- **수정 방향**: `logger.warning()` 추가

### L-9. VoiceRecorder 접근성 부족
- **파일**: `frontend/components/input/VoiceRecorder.tsx:89-97`
- **문제**: 녹음 상태 표시에 `aria-live` 영역 없음. 스크린 리더가 상태 변화 알림 불가.
- **수정 방향**: `aria-live="polite"` 영역 추가
