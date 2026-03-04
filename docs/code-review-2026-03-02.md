# 코드 리뷰 결과 — 2026-03-02

> Codex MCP 멀티에이전트 병렬 분석 (8개 파일 동시)
> 리뷰어: Codex gpt-5.3-codex + Claude Opus 4.6

## High (6건 — 즉시 수정 권장)

### H1. XSS — AI 응답 HTML 미살균
- **파일**: `services/ai_service.py:277,280` + `routes/blog_routes.py:712,714,724`
- **코드**:
  ```python
  html = markdown.markdown(body, ...)
  html = f"<pre>{body}</pre>"
  ```
- **문제**: AI 모델 응답을 HTML로 변환 시 sanitize 없음. 악의적 프롬프트 주입으로 XSS 가능.
- **수정**: `bleach.clean()` allowlist 적용, fallback은 `html.escape()` 사용.

### H2. SSRF — 외부 caption URL 무검증 fetch
- **파일**: `services/content_service.py:444,454,498`
- **코드**:
  ```python
  response = requests.get(url, ...)
  text = _download_caption_from_url(track.get('baseUrl', ''))
  ```
- **문제**: YouTube 자막 `baseUrl`을 검증 없이 fetch. 내부망 스캔 가능.
- **수정**: https 강제, 호스트 allowlist, private/loopback IP 차단, 리디렉트 비활성화.

### H3. 함수 중복 정의 — 이전 정의 덮어쓰기
- **파일**: `services/content_service.py:742~1079`
- **코드**:
  ```python
  def get_playlist_videos(url: ...):   # 첫 번째 정의
  ...
  def get_playlist_videos(playlist_id: ...):  # 두 번째 정의 (덮어씀)
  ```
- **문제**: `get_playlist_videos`, `is_playlist_url`, `get_channel_videos` 등 동일 이름 함수가 파일 하단에서 재정의되어 상단 버전이 무시됨.
- **수정**: 이름 분리 (`*_from_url`, `*_by_id`) 또는 하나로 통합 후 호출부 업데이트.

### H4. SSRF — 웹훅 URL 무검증
- **파일**: `services/webhook_service.py:15,36,56`
- **코드**:
  ```python
  self.url = url
  requests.post(self.url, ...)
  ```
- **문제**: 사용자 제공 웹훅 URL을 검증 없이 POST. 내부 서비스 공격 가능.
- **수정**: scheme/host 검증, private IP 차단, allowlist 적용.

### H5. 리소스 누수 — tmp_path 미초기화
- **파일**: `services/whisper_service.py:30,55-57`
- **코드**:
  ```python
  fd, tmp_path = tempfile.mkstemp(...)
  ...
  _cleanup_file(tmp_path)
  ```
- **문제**: `tempfile.mkstemp()` 전에 예외 발생 시 `tmp_path` 미정의 → `UnboundLocalError` + 임시 파일 잔류.
- **수정**: `tmp_path = None` 초기화, `finally`에서 None 체크 후 cleanup.

### H6. IDOR — 워크스페이스 권한 미검증
- **파일**: `routes/auth_routes.py:622-631`
- **코드**:
  ```python
  @require_auth
  def get_workspace_members(workspace_id):
      members = workspace_service.get_members(workspace_id)
  ```
- **문제**: 인증만 확인하고 해당 워크스페이스 소속 여부/권한 미확인. 다른 워크스페이스 멤버 목록 조회 가능.
- **수정**: 호출자가 해당 워크스페이스 멤버(또는 Owner)인지 검증 추가.

---

## Medium (14건 — 개선 권장)

### M1. `re` import 누락
- **파일**: `services/ai_service.py:92,98`
- **문제**: `_extract_keywords()`에서 `re.search()`, `re.sub()` 사용하지만 `import re` 없음 → `NameError`.

### M2. GLM 락 범위 과다
- **파일**: `services/ai_service.py:21,109,235,240,252`
- **문제**: `_glm_lock`이 네트워크 호출 + `time.sleep()` 동안 유지 → 모든 GLM 요청 head-of-line blocking.
- **수정**: 최소 임계 구간만 락, 재시도/백오프는 락 밖에서.

### M3. 에러 상세 클라이언트 노출
- **파일**: `services/ai_service.py:198,295,331,388,394`, `routes/auth_routes.py:152,183,215,226,254,271`, `services/content_service.py:504-505`, `services/webhook_service.py:40,42,44,59,60`
- **문제**: `str(e)` 그대로 응답에 포함 → 내부 정보 유출.
- **수정**: 클라이언트에는 generic 에러, 상세는 서버 로그에만.

### M4. video_id 미검증
- **파일**: `services/content_service.py:96-97,112,545,685`
- **문제**: 잘못된 `video_id`가 제어되지 않은 `ValueError` 유발 → 500 에러.

### M5. SSE 스키마 불일치
- **파일**: `services/pipeline_service.py:80-84`
- **문제**: `step_error` 이벤트에 `progress` 필드 누락, 클라이언트 파싱 불일치 가능.

### M6. 가변 steps 공유
- **파일**: `services/pipeline_service.py:28,34-35,56`
- **문제**: 공유 가변 `steps` 리스트가 동시 실행 시 변경될 수 있음.
- **수정**: `tuple(config.steps)`로 불변 스냅샷.

### M7. context 직접 변경
- **파일**: `services/pipeline_service.py:37,70,87`
- **문제**: `context.update(result)`로 호출자 딕셔너리 직접 변경 → 재사용 시 상태 오염.

### M8. 웹훅 재시도 로직
- **파일**: `services/webhook_service.py:34,37,40`
- **문제**: 4xx(비재시도 대상)에도 즉시 재시도. backoff/jitter 없음.

### M9. Whisper temp 잔류
- **파일**: `services/whisper_service.py:35,52,57`
- **문제**: `.wav` 파일만 삭제, yt-dlp의 기타 임시 파일 잔류.

### M10. HTML 미살균 (blog_routes)
- **파일**: `routes/blog_routes.py:712,714,724`
- **문제**: H1과 동일 패턴이 라우트 레벨에도 존재.

### M11. 사용량 TOCTOU
- **파일**: `routes/blog_routes.py:653-654,717-718,730-735`
- **문제**: `check_can_use()` → `decrement()` 비원자적 → 동시 요청 시 초과 사용 가능.

### M12. 오픈 리디렉트
- **파일**: `routes/auth_routes.py:141-147`
- **문제**: OAuth `redirect_url`을 클라이언트 입력 그대로 사용.

### M13. 계정 존재 여부 노출
- **파일**: `routes/auth_routes.py:120-121`
- **문제**: 비밀번호 리셋 시 "not found" 여부로 계정 존재 확인 가능.

### M14. config 파싱 + 프로바이더 불일치
- **파일**: `config.py:42,96-121,137-142,149`
- **문제**: env 값 잘못되면 import 시 crash, `get_provider_from_model()`과 `SUPPORTED_PROVIDERS` 매핑 불일치, ollama 기본 활성화.

---

## 수정 우선순위 제안

1. **보안 (H1,H2,H4,H6,M12)** — XSS, SSRF, IDOR, 오픈 리디렉트
2. **버그 (H3,H5,M1)** — 함수 덮어쓰기, 리소스 누수, import 누락
3. **안정성 (M2,M6,M7,M11)** — 락 범위, 가변 상태, TOCTOU
4. **정보 보호 (M3,M4,M13)** — 에러 노출, 계정 열거
5. **품질 (M5,M8,M9,M14)** — SSE 스키마, 재시도 로직, temp 정리, config 파싱
