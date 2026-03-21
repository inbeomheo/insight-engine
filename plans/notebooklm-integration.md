# Plan: NotebookLM 통합 — 멀티미디어 콘텐츠 생성 연동

> Source PRD: https://github.com/inbeomheo/insight-engine/issues/5

## Architectural decisions

- **Routes**: `/api/notebooklm/` 접두사. 4개 엔드포인트 — `generate`, `status/<artifact_id>`, `download/<artifact_id>`, `auth-check`
- **서비스 위치**: `services/notebooklm/notebooklm_service.py` — `nlm` CLI subprocess 래핑
- **노트북 관리**: 단일 노트북 고정 재사용. 노트북 ID를 `data/notebooklm_state.json`에 저장
- **소스 중복 방지**: YouTube URL 기준으로 이미 추가된 소스인지 확인 (state 파일에 URL→source_id 매핑 저장)
- **비동기 패턴**: 생성 요청 즉시 artifact_id 반환 → 프론트엔드 5초 폴링
- **콘텐츠 타입**: audio, video, infographic, slide_deck, mindmap, quiz, flashcards, report(briefing), report(study_guide) — 총 9종
- **프론트엔드 상태**: Report 타입에 `notebooklm?: { artifacts: NotebookLmArtifact[] }` 추가. Zustand store에서 관리
- **제거 대상**: 기존 TTS 팟캐스트 변환 (`handleTts`), 마인드맵 모달 (`setMindmapModalOpen`)

---

## Phase 1: 백엔드 서비스 + 인증 + 팟캐스트 end-to-end

**User stories**: #1, #12, #13, #17

### What to build

`nlm` CLI를 subprocess로 래핑하는 NotebookLM 서비스를 만든다. 서버 시작 시 또는 첫 요청 시 노트북 존재 여부를 확인하고, 없으면 자동 생성한다. 콘텐츠 생성 요청이 오면 자막 텍스트를 소스로 추가(중복 체크)하고, `nlm audio create`를 실행하여 artifact_id를 반환한다. 상태 폴링 엔드포인트로 생성 진행 상태를 확인할 수 있다. 인증 체크 엔드포인트로 `nlm login --check`의 결과를 반환한다.

이 Phase 완료 시 `curl`로 팟캐스트 생성 요청 → 상태 폴링 → 완료 확인까지 가능하다.

### Acceptance criteria

- [ ] `POST /api/notebooklm/generate` 호출 시 노트북 자동 생성 + 소스 추가 + 팟캐스트 생성 시작, artifact_id 반환
- [ ] `GET /api/notebooklm/status/<artifact_id>` 호출 시 `in_progress` / `completed` / `failed` 상태 반환
- [ ] 동일 YouTube URL로 재요청 시 소스 중복 추가 없이 기존 source_id 재사용
- [ ] `GET /api/notebooklm/auth-check` 호출 시 인증 상태 + 계정 이메일 반환
- [ ] 인증 만료 시 적절한 에러 메시지 반환 (`nlm login` 안내 포함)
- [ ] `notebooklm_service.py` 단위 테스트 — subprocess mock으로 노트북 생성/소스 추가/생성/상태 폴링 검증

---

## Phase 2: 프론트엔드 메뉴 + 폴링 + 결과 표시 (팟캐스트)

**User stories**: #10, #11, #14, #18

### What to build

ResultCard 더보기 메뉴에 "NotebookLM 팟캐스트" 항목을 추가한다. 클릭 시 `/api/notebooklm/generate` API를 호출하고, 카드에 진행 상태 표시(스피너 + "팟캐스트 생성 중...")를 보여준다. 5초 간격으로 상태를 폴링하다가 완료되면 카드 하단에 NotebookLmSection을 렌더링하여 `<audio>` 플레이어 + 다운로드 버튼을 표시한다.

기존 "팟캐스트로 변환" (TTS) 메뉴 항목과 관련 코드를 제거한다.

에러 발생 시 에러 메시지 + 재시도 버튼을 표시한다. 인증 미완료 시 "nlm login 필요" 안내를 표시한다.

### Acceptance criteria

- [ ] 더보기 메뉴에 "NotebookLM 팟캐스트" 항목이 표시됨
- [ ] 클릭 시 카드에 "생성 중" 진행 표시가 나타남
- [ ] 생성 완료 시 카드 하단에 오디오 플레이어가 렌더링됨
- [ ] 기존 "팟캐스트로 변환" (TTS) 메뉴가 제거됨
- [ ] 에러 시 에러 메시지 + 재시도 버튼 표시
- [ ] 인증 미완료 시 안내 메시지 표시
- [ ] Report 타입에 `notebooklm` 필드 추가, Zustand store 연동

---

## Phase 3: 나머지 8개 콘텐츠 타입 확장

**User stories**: #2, #3, #4, #5, #6, #7, #8, #9

### What to build

Phase 1의 generate 엔드포인트에 `type` 파라미터를 확장하여 비디오, 인포그래픽, 슬라이드, 마인드맵, 퀴즈, 플래시카드, 브리핑, 스터디 가이드를 지원한다. 각 타입별 `nlm` CLI 명령어 매핑과 옵션(포맷, 스타일 등)을 서비스에 추가한다.

프론트엔드 더보기 메뉴에 "NotebookLM" 서브메뉴 그룹으로 9개 항목을 구성한다. NotebookLmSection에서 각 타입별 렌더링을 분기한다:
- 비디오: 썸네일 + 다운로드
- 인포그래픽/슬라이드: 이미지 미리보기 + 다운로드
- 텍스트(퀴즈/플래시카드/브리핑/스터디가이드): 접기/펼치기 텍스트
- 마인드맵: 마인드맵 뷰어

### Acceptance criteria

- [ ] 9개 콘텐츠 타입 모두 더보기 메뉴에서 선택 가능
- [ ] 각 타입별 generate 요청이 올바른 `nlm` CLI 명령으로 변환됨
- [ ] 비디오 완료 시 썸네일 + 다운로드 버튼 렌더링
- [ ] 인포그래픽 완료 시 이미지 미리보기 + 다운로드 렌더링
- [ ] 슬라이드 완료 시 미리보기 + 다운로드 렌더링
- [ ] 텍스트 타입(퀴즈/플래시카드/브리핑/스터디가이드) 접기/펼치기로 표시
- [ ] 마인드맵 뷰어에 결과 표시
- [ ] 여러 타입을 순차적으로 생성해도 각각 독립적으로 표시

---

## Phase 4: 다운로드 + 중복 기능 제거 + 정리

**User stories**: #15, #16

### What to build

파일 다운로드 엔드포인트를 완성한다. `nlm download` 명령으로 파일을 서버 임시 디렉토리에 받고, 프론트엔드에 스트리밍 응답으로 전달한다. 임시 파일은 전송 후 정리한다.

기존 마인드맵 모달(`setMindmapModalOpen`)과 관련 코드를 제거하고, NotebookLM 마인드맵으로 완전 대체한다.

최종 정리: 미사용 import 제거, 타입 정리, 에러 핸들링 일관성 점검.

### Acceptance criteria

- [ ] `GET /api/notebooklm/download/<artifact_id>` 호출 시 파일 다운로드 응답 반환
- [ ] 오디오(.mp3), 비디오(.mp4), 슬라이드(.pdf/.pptx) 다운로드 동작 확인
- [ ] 기존 마인드맵 모달 및 관련 코드 완전 제거
- [ ] 미사용 import, 죽은 코드 정리 완료
- [ ] 모든 Phase 1~3의 acceptance criteria가 여전히 통과
