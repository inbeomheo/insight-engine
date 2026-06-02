# Insight Engine 스튜디오형 전면 재구성 디자인 스펙

작성일: 2026-06-03
대상: `frontend` 중심, 기존 Flask API/생성 기능 유지
목표: Insight Engine을 “URL/텍스트 입력 도구”가 아니라 “AI 콘텐츠 제작 스튜디오”로 재구성한다.

## 1. 문제 정의

현재 앱은 기능이 많지만 사용자는 다음을 한눈에 이해하기 어렵다.

- 무엇을 넣으면 어떤 결과가 나오는지
- 생성 전 어떤 설정이 적용되는지
- 생성 후 NLM, 변환, 내보내기, 예약 발행을 어디서 해야 하는지
- 히스토리, 캘린더, 결과 카드가 각각 어떤 작업 흐름에 속하는지

따라서 앱의 정보구조를 “입력 → 제작 설정 → 생성 → 후처리 → 발행/저장” 흐름으로 재정렬한다.

## 2. 제품 컨셉

**AI Content Studio for Video-to-Publishing**

YouTube/웹/텍스트/팟캐스트 소스를 넣으면, 사용자가 원하는 산출물 세트로 변환하고, NotebookLM 보조자료·플랫폼 변환·내보내기·예약까지 한 작업실에서 끝내는 제품이다.

## 3. 핵심 원칙

1. **작업 흐름 우선**: 기능 나열 대신 단계별 제작 흐름을 보여준다.
2. **설정은 숨기지 않되 압축**: 핵심 설정은 상단 작업 패널, 고급 설정은 접이식으로 둔다.
3. **결과는 작업 카드**: 결과 카드는 읽기 전용 문서가 아니라 후처리 액션 허브다.
4. **NLM은 별도 메뉴가 아니라 산출물 패널**: 생성 중/완료/보기 상태를 카드 안에서 명확히 표시한다.
5. **발행 기능은 예약 중심**: 직접 CMS 발행 버튼은 제거된 상태를 유지하고, 예약/내보내기/공유를 우선한다.

## 4. 새 화면 구조

```txt
┌──────────────────────────────────────────────────────────────┐
│ Header: Insight Studio | 모델 | 작업상태 | 설정              │
├───────────────┬──────────────────────────────┬───────────────┤
│ Left Rail     │ Main Studio                  │ Right Panel   │
│ - 새 작업     │ 1. Source Composer           │ - 작업 요약   │
│ - 히스토리    │ 2. Output Blueprint          │ - 최근 산출물 │
│ - 예약 캘린더 │ 3. Generate CTA              │ - 빠른 액션   │
│ - 워크스페이스│ 4. Result Workbench          │               │
└───────────────┴──────────────────────────────┴───────────────┘
```

모바일에서는 `Left Rail`과 `Right Panel`을 drawer로 전환한다.

## 5. 기능 재배치

### 5.1 Source Composer

현재 `UrlInput`, `TextInput`을 통합한다.

- 탭: URL / 텍스트 / 파일 / 음성
- URL 입력은 YouTube, 웹페이지, RSS, arXiv, Podcast 지원 문구 유지
- 텍스트 입력은 URL이 없을 때만 보이는 구조를 제거하고 항상 선택 가능하게 한다.
- 여러 소스가 들어오면 source chip 목록으로 표시한다.

### 5.2 Output Blueprint

현재 설정 팝오버에 숨어 있는 값을 작업 전면으로 끌어낸다.

- 산출물 타입: Blog+SEO, 요약, 튜토리얼, Q&A, SNS, 뉴스레터, 코스 등
- 제작 모드: 개별 / 통합 / 퓨전 분석
- 톤·길이·언어
- 웹 검색 보강, 댓글 심층 분석, 에이전트 모드
- 선택된 모델/provider

### 5.3 Generate CTA

생성 버튼은 현재 URL 개수와 제작 모드에 따라 하나의 주 버튼으로 통합한다.

예:
- `1개 소스로 콘텐츠 생성`
- `3개 소스 각각 생성`
- `3개 소스 통합 콘텐츠 생성`
- `퓨전 분석 시작`

### 5.4 Result Workbench

`ResultCard`의 액션 메뉴를 다음 섹션으로 재구성한다.

- 읽기: 본문, HTML/Markdown preview, 타임라인 보기
- 개선: 플랫폼 변환, 프롬프트 보기, 이벤트 추출, 영상 Q&A
- NLM 산출물: 팟캐스트, 비디오, 인포그래픽, 슬라이드, 마인드맵, 퀴즈, 플래시카드, 브리핑, 스터디가이드
- 내보내기: HTML, DOCX, Markdown, TXT, ZIP, PDF 인쇄
- 배포: 예약 발행, 공유
- 관리: 삭제

### 5.5 Right Panel

새 보조 패널을 둔다.

- 현재 작업 설정 요약
- 생성 결과 수 / 실패 수 / 예약 수
- 최근 NotebookLM 산출물
- 바로가기: 전체 내보내기, 예약 캘린더, 설정

## 6. 디자인 시스템

### 6.1 톤

- 기존 인디고/퍼플 브랜드를 유지하되 더 차분한 스튜디오 느낌으로 조정
- 흰 배경 + 미세한 slate surface + 명확한 카드 계층
- 그라디언트는 로고/주 CTA/상태 강조에만 사용

### 6.2 색상

- Background: `#F6F7FB`
- Surface: `#FFFFFF`
- Surface muted: `#F1F5F9`
- Text primary: `#0F172A`
- Text secondary: `#64748B`
- Border: `#E2E8F0`
- Primary: `#4F46E5`
- Primary soft: `#EEF2FF`
- Purple accent: `#7C3AED`
- Success: `#059669`
- Warning: `#D97706`
- Error: `#DC2626`

### 6.3 컴포넌트 스타일

- Shell: 좌측 280px, 우측 320px, 중앙 minmax 680~960px
- Card: radius 20px, border `#E2E8F0`, shadow minimal
- Buttons: 주 CTA 44~48px, 보조 액션 36~40px
- Input: 크고 명확한 composer 형태, placeholder보다 helper text 우선
- Status: loading/pending/completed/failed badge 명확화

## 7. 코드 아키텍처 계획

새 컴포넌트 후보:

```txt
frontend/components/studio/
  StudioShell.tsx
  StudioHeader.tsx
  StudioSidebar.tsx
  SourceComposer.tsx
  OutputBlueprint.tsx
  GenerateDock.tsx
  StudioRightPanel.tsx
  WorkbenchEmptyState.tsx
```

기존 컴포넌트 재사용:

- `UrlInput` 로직은 `SourceComposer`로 흡수 또는 래핑
- `TextInput` 로직은 항상 접근 가능한 탭으로 이동
- `ResultCard`는 `ResultWorkbenchCard` 방향으로 정리
- `FilterBar`, `ViewModeSelector`는 결과 목록 toolbar로 유지
- `ScheduleModal`, `NotebookLmSection`, `PromptModal`, `MindmapModal` 유지

## 8. 데이터 흐름

1. 사용자가 Source Composer에서 소스 입력
2. Output Blueprint에서 산출물/모드/톤 설정
3. Generate CTA가 `useGenerate`의 기존 함수 호출
4. 생성 결과는 `resultStore.reports`에 저장
5. Result Workbench가 결과별 액션 수행
6. NLM/예약/내보내기 상태는 카드와 Right Panel에 반영

기존 Flask API는 유지한다. 이번 재구성은 우선 프론트 정보구조와 UX를 바꾸는 작업이다.

## 9. 테스트 기준

완료 판정에는 다음 증거가 필요하다.

- `npm run lint --prefix frontend` 통과
- `tsc --noEmit` 통과
- ChatMock 5.5 Auto QA 통과, Failures 0
- 브라우저에서 직접 확인:
  - 첫 화면이 스튜디오 레이아웃으로 보임
  - URL 입력 생성 정상
  - 텍스트 입력 생성 정상
  - 복수 URL 모드 전환 정상
  - 결과 카드 액션 메뉴 정상
  - NLM 생성 중/완료 표시 정상
  - Markdown 계열 NLM 산출물은 브라우저 보기로 열림
  - 내보내기/예약/공유/삭제 정상

## 10. 단계별 구현

### Phase 1: Visual Shell

- 전역 배경/색상 토큰 조정
- Header/Sidebar를 Studio 톤으로 변경
- 중앙 main 영역을 Studio layout으로 변경
- Right Panel 기본 구조 추가

### Phase 2: Source + Blueprint

- URL/텍스트 입력을 Source Composer로 재배치
- 설정 요약/산출물 선택을 Output Blueprint로 재배치
- 생성 CTA 문구와 모드 표시 개선

### Phase 3: Workbench

- 결과 리스트 toolbar 정리
- ResultCard 헤더/메타/액션 영역 재구성
- NLM 섹션을 산출물 패널처럼 보이게 개선

### Phase 4: Polish + QA

- 빈 상태/로딩/오류 상태 개선
- 반응형 drawer 처리
- 전체 자동 QA와 수동 웹 QA 수행
- 문서/QA_REPORT 업데이트

## 11. 비범위

이번 재구성에서 하지 않는다.

- Flask API 대규모 변경
- 인증/결제/워크스페이스 백엔드 재설계
- 직접 CMS 발행 기능 복구
- 새 AI provider 추가

## 12. 성공 기준

사용자가 앱을 열었을 때 즉시 다음을 이해해야 한다.

1. “여기에 소스를 넣는다.”
2. “이 설정으로 어떤 산출물을 만들지 고른다.”
3. “생성 후 여기서 NLM/내보내기/예약까지 한다.”
4. “내 작업 히스토리와 예약 상태가 어디 있는지 안다.”

이 네 가지가 웹 UI와 QA 증거로 확인되면 전면 재구성 1차 목표를 완료로 본다.
