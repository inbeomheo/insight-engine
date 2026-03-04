# 코드 최적화 검토 보고서 (2026-03-02)

## 범위
- 백엔드: `routes/`, `services/`
- 프론트엔드: `frontend/hooks`, `frontend/components`, `frontend/app`
- 관점: 실행 성능, 자원 효율, 동시성, 불필요 연산, 회귀 위험

## 주요 발견사항 (심각도 순)

### 1) Critical: Fusion 코멘트 수집이 항상 실패하도록 호출 시그니처 불일치
- 근거:
  - `services/fusion_service.py`에서 `get_top_comments`를 인자 2개로 호출함 ([services/fusion_service.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/services/fusion_service.py:63))
  - 실제 정의는 인자 1개 (`video_id`)만 받음 ([services/content_service.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/services/content_service.py:781))
- 영향:
  - 코멘트 수집 Future가 `TypeError`를 내고 무시되어, Fusion 품질이 저하됨
  - 실패 예외 생성/처리 오버헤드가 URL 수만큼 반복됨
- 권장:
  - 호출 시그니처 정합화 (`get_top_comments(video_id)`로 수정, 필요 시 함수 시그니처 확장)
  - 회귀 테스트 추가: Fusion에서 코멘트가 실제 포함되는지 검증

### 2) High: `useGenerate`의 stale closure로 최신 설정값(웹검색/에이전트모드) 미반영 가능
- 근거:
  - 콜백 내부에서 `enableWebSearch`, `enableAgentMode` 사용 ([frontend/hooks/useGenerate.ts](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/frontend/hooks/useGenerate.ts:39))
  - `useCallback` dependency에 두 값이 빠져 있음 ([frontend/hooks/useGenerate.ts](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/frontend/hooks/useGenerate.ts:100))
- 영향:
  - 사용자가 토글을 바꿔도 생성 요청 payload에 이전 값이 들어갈 수 있음
  - 설정 변경 직후 요청에서 예측 불가능한 동작 발생
- 권장:
  - dependency 배열에 `enableWebSearch`, `enableAgentMode` 추가
  - E2E/훅 테스트 추가: 토글 변경 후 첫 요청 payload 검증

### 3) High: AI 캐시 접근마다 SQLite 연결 생성 + PRAGMA 재설정
- 근거:
  - `_get_conn()`에서 호출마다 `sqlite3.connect`와 PRAGMA 실행 ([services/cache_service.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/services/cache_service.py:23))
  - `get/put/evict`가 매번 `_get_conn()` 사용 ([services/cache_service.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/services/cache_service.py:55), [services/cache_service.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/services/cache_service.py:79), [services/cache_service.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/services/cache_service.py:96))
- 영향:
  - 캐시 hit가 잦을수록 연결 생성/해제 비용이 누적
  - 고빈도 요청에서 응답시간 지터 증가 가능
- 권장:
  - 스레드 로컬 연결 재사용 또는 간단한 연결 풀 적용
  - PRAGMA는 초기화 시 1회 설정하도록 구조 분리

### 4) Medium: Transcript 성공 경로에서 추가 YouTube API 조회 1회 발생
- 근거:
  - transcript fetch 성공 후 `_detect_auto_caption()` 호출 ([services/content_service.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/services/content_service.py:644))
  - `_detect_auto_caption()` 내부에서 `ytt_api.list(video_id)` 재호출 ([services/content_service.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/services/content_service.py:574))
- 영향:
  - 성공 케이스마다 외부 API 호출 1회 추가
  - 네트워크 지연/쿼터 사용량 증가
- 권장:
  - 기존 fetch 단계에서 얻은 트랙 메타를 재사용하여 재호출 제거

### 5) Medium: 대형 카드 리스트에서 Markdown 렌더링을 항상 선계산
- 근거:
  - `processedContent`/`markdownBody`가 모든 렌더에서 계산됨 ([frontend/components/result/ResultCard.tsx](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/frontend/components/result/ResultCard.tsx:264), [frontend/components/result/ResultCard.tsx](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/frontend/components/result/ResultCard.tsx:269))
  - 이후에 compact/timeline/collapsed 분기 ([frontend/components/result/ResultCard.tsx](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/frontend/components/result/ResultCard.tsx:279), [frontend/components/result/ResultCard.tsx](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/frontend/components/result/ResultCard.tsx:465))
- 영향:
  - 카드 수 증가 시 초기 렌더/필터 변경 비용 급증
  - compact 모드에서도 불필요한 Markdown 파싱 비용 발생
- 권장:
  - `collapsed === false`이고 실제 본문 영역이 렌더될 때만 Markdown 계산
  - 카드가 많아질 경우 리스트 가상화 검토

### 6) Medium: 동일 요청에서 `request.get_json()` 중복 호출
- 근거:
  - `/generate` 흐름에서 body 파싱을 여러 번 수행 ([routes/blog_routes.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/routes/blog_routes.py:340), [routes/blog_routes.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/routes/blog_routes.py:355))
  - `/api/pipeline`에서도 `_get_request_data()` 후 다시 `get_json()` 호출 ([routes/advanced_routes.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/routes/advanced_routes.py:382), [routes/advanced_routes.py](/E:/자동화 프로젝트/250705_스마트 콘텐츠 생성기(완성)/routes/advanced_routes.py:383))
- 영향:
  - 경미하지만 빈번 endpoint에서는 누적 오버헤드
  - request body 처리 지점이 분산되어 유지보수 복잡도 증가
- 권장:
  - 각 핸들러당 JSON 파싱 1회로 통합, 필요한 필드만 구조화

## 빠른 개선 우선순위
1. Fusion 코멘트 수집 시그니처 버그 수정 (즉시)
2. `useGenerate` dependency 누락 수정
3. 캐시 DB 연결 재사용 적용
4. Transcript 경로의 중복 API 호출 제거
5. ResultCard Markdown 지연 계산/가상화

## 테스트 공백
- `tests/test_fusion_service.py`는 `get_top_comments` 호출 인자 검증이 없어 현재 버그를 놓치고 있음.
- 프론트 훅 테스트에서 설정 토글 변경 직후 요청 payload를 검증하는 케이스가 필요함.
