# Autoresearch Session — Insight Engine Frontend

## 프로젝트
Insight Engine (Next.js 16 + Tailwind v4)

## 개선 목표
UX 개선 → 성능 최적화 → 접근성 + 시각 피드백 → 디자인 품질 → **접근성 심화 WCAG AA** (Outer Loop Round 3)

## 현재 상태
- Phase: Outer Loop Round 4 완료 (시각적 정합성 — shadow/마이크로인터랙션 통일)
- Inner Loop 실행 수: 45 (keep 36, revert 9)
- Outer Loop 실행 수: 5
- **최고 복합 점수: 99.45/100** (실험 41~45, 접근성 가중치 기준)
- **수렴 상태**: converged=true, keep_rate=100%

## 베이스라인
- **복합 점수: 71.75/100** (UX 가중치 기준)
- error_score: 40 (콘솔 에러 3개 — icon-192.png 404, /api/workspaces 400 x2)
- dom_score: 100 (접근성 구조 양호, 랜드마크 존재)
- form_score: 80 (URL 입력 필드 존재, 인터랙션 가능)
- visual_score: 85 (레이아웃 정상)

## 최근 점수
- error_score: 100 (콘솔 에러 0)
- dom_score: 100 (접근성 랜드마크/역할 양호)
- form_score: 99 (aria-pressed, radiogroup, switch, focus-visible, aria-expanded, aria-haspopup, aria-describedby 등)
- visual_score: 98 (shadow 통일, 활성 카드 깊이감, 드래그 오버레이 개선, 버튼 마이크로인터랙션 일관성)

## Outer Loop 전략 기록

| 라운드 | 전략 | 실험 수 | keep율 | 최종 점수 | Outer Score | 수렴 |
|--------|------|---------|--------|-----------|-------------|------|
| 0 | UX 개선 (접근성, 인터랙션, 피드백) | 20 | 55.0% | 98.2 | 65.63 | No |
| 1 | 성능 최적화 (memo, useCallback, 리렌더 방지) | 5 | 100.0% | 98.2 | 65.23 | Yes |
| 2 | 접근성 + 시각 피드백 강화 (focus-visible, role, hover) | 5 | 100.0% | 98.6 | — | — |
| 3 | 디자인 품질 (마이크로인터랙션, 트랜지션, 간격/shadow) | 5 | 100.0% | 98.9 | 51.69 | Yes |
| 4 | 접근성 심화 WCAG AA (aria-expanded, role=switch, aria-haspopup, aria-describedby) | 5 | 100.0% | 99.3 | 50.87 | Yes |
| 5 | 시각적 정합성 (shadow 통일, 활성 카드 깊이, 드래그 오버레이, 버튼 인터랙션) | 5 | 100.0% | 99.45 | — | Yes |

## Outer Loop Round 4 결과 (시각적 정합성)

| # | 가설 | 점수 | 판정 |
|---|------|------|------|
| 41 | 활성 카드 shadow-md shadow-primary/5 깊이감 추가 | 99.45 | keep |
| 42 | 에러 메시지 shadow-sm shadow-destructive/5 계층 강화 | 99.45 | keep |
| 43 | combined/fusion 버튼 shadow-md 통일 + hover:shadow-lg | 99.45 | keep |
| 44 | 드래그 오버레이 border/rounded-xl 강화 + 아이콘 bounce | 99.45 | keep |
| 45 | 더 보기 버튼 hover:shadow-md active:scale 마이크로인터랙션 | 99.45 | keep |

**keep 비율: 5/5 (100%)** — 모두 조건부 렌더링 블록 내 변경으로 hydration 에러 회피

## Outer Loop Round 3 결과 (접근성 심화 WCAG AA)

| # | 가설 | 점수 | 판정 |
|---|------|------|------|
| 36 | ResultCard 접기/펼치기 버튼 aria-expanded 추가 | 99.3 | keep |
| 37 | SettingsPopover 웹 검색 보강 토글 role=switch + aria-checked | 99.3 | keep |
| 38 | NlpAnalysisSection 접기/펼치기 aria-expanded 추가 | 99.3 | keep |
| 39 | ResultCard 더보기 메뉴 aria-haspopup=menu 추가 | 99.3 | keep |
| 40 | SettingsPopover dialog aria-describedby 설명 텍스트 연결 | 99.3 | keep |

**keep 비율: 5/5 (100%)** — 모두 조건부 렌더링 블록 내 변경으로 hydration 에러 회피

## Outer Loop Round 2 결과 (디자인 품질)

| # | 가설 | 점수 | 판정 |
|---|------|------|------|
| 31 | LoadingSkeleton 패딩/간격/shadow 개선 (border-border/40, px-5, gap-2.5) | 98.3 | keep |
| 32 | URL 칩 hover shadow + 삭제 버튼 hover:scale-110 마이크로인터랙션 | 98.3 | keep |
| 33 | 생성 버튼 active:scale-[0.98] + hover:shadow-lg 마이크로인터랙션 | 98.6 | keep |
| 34 | SettingsPopover 스타일/길이/문체/언어 버튼 active:scale-95 + hover:shadow-sm | 98.6 | keep |
| 35 | 히스토리 항목 활성 상태 border-primary/20 + duration-200 트랜지션 | 98.9 | keep |

**keep 비율: 5/5 (100%)** — 조건부 렌더링 블록 내 변경으로 hydration 에러 회피

## Inner Loop Round 3 결과 (접근성 + 시각 피드백)

| # | 가설 | 점수 | 판정 |
|---|------|------|------|
| 26 | SettingsPopover 스타일/길이/문체/언어 버튼 focus-visible 링 추가 | 98.45 | keep |
| 27 | GenerationModeSelector radiogroup+radio+aria-checked | 98.45 | keep |
| 28 | FusionOptions role=group + aria-label | 98.45 | keep |
| 29 | 에이전트 모드 토글 role=switch + aria-checked + focus-visible | 98.45 | keep |
| 30 | ResultCard hover 트랜지션 강화 (border + transition-all) | 98.6 | keep |

**keep 비율: 5/5 (100%)**

## Outer Loop Round 1 결과 (성능 최적화)

| # | 가설 | 점수 | 판정 |
|---|------|------|------|
| 21 | FilterBar+LoadingSkeleton memo 감싸기 | 98.20 | keep |
| 22 | UrlInput memo + onToggleSettings useCallback | 98.20 | keep |
| 23 | handleGenerate/Merged/Fusion useCallback | 98.20 | keep |
| 24 | Header memo + Zustand selector 분리 | 98.20 | keep |
| 25 | ScheduleModal/HelpPanel/GuidedTour 인라인 함수 제거 | 98.20 | keep |

**keep 비율: 5/5 (100%)**

## 핵심 학습

### 하이드레이션 에러 패턴 (UX 라운드에서 학습)
- Next.js SSR + Turbopack 환경에서 **항상 렌더되는 컴포넌트**의 className/속성/태그 변경은 하이드레이션 에러를 유발
- **안전한 수정 대상**: 조건부로 렌더되는 컴포넌트 (reports.length > 0, urls.length > 0, settingsPopoverOpen 등)
- **위험한 수정 대상**: Sidebar 빈 상태, Header span→h1, 검색 바 role 추가 등 SSR 시 렌더되는 컴포넌트
- **Turbopack SSR 캐시 버그**: HMR로 코드 변경 시 클라이언트 번들만 업데이트되고 SSR 번들은 이전 상태 유지. 서버 재시작(.next 삭제 포함)으로만 해결 가능
- **`reports.length === 0` 빈 상태도 SSR 렌더됨**: 초기 상태에서 reports가 빈 배열이므로 빈 상태 UI도 SSR 시점에 렌더됨 — className 변경 시 하이드레이션 에러 유발 (Round 2 실험 31에서 확인)

### 성능 최적화 패턴 (Round 1에서 학습)
- `React.memo`는 props가 바뀌지 않는 자식 컴포넌트에 효과적
- 인라인 함수 → `useCallback`은 memo된 자식 컴포넌트에 전달될 때만 의미 있음
- `useUIStore()` 구조분해보다 개별 selector가 더 효율적

### 접근성 + 시각 피드백 패턴 (Round 2에서 학습)
- `focus-visible:ring-2`는 키보드 접근성에 필수 (마우스 클릭 시에는 표시 안 됨)
- `role="radiogroup"` + `role="radio"` + `aria-checked`는 세그먼트 컨트롤의 표준 패턴
- `role="switch"` + `aria-checked`는 토글 버튼의 표준 패턴
- ResultCard의 `hover:border-border/60`은 미묘하지만 시각적 피드백 향상

### 디자인 품질 패턴 (Round 3에서 학습)
- `active:scale-[0.98]` / `active:scale-95`: 버튼 누르는 느낌의 미묘한 축소 — 터치 피드백 강화
- `hover:shadow-sm` / `hover:shadow-lg`: 호버 시 elevation 변화로 인터랙티브 요소 강조
- `transition-all duration-200`: 색상뿐 아니라 shadow/scale 변화도 부드럽게 전환
- `border border-transparent` → `border border-primary/20`: 활성 상태의 미묘한 테두리로 시각적 구분
- LoadingSkeleton의 `px-5 gap-2.5 rounded`: 넉넉한 패딩과 간격은 정제된 느낌 제공

### 접근성 심화 패턴 (Round 4에서 학습)
- `aria-expanded`: 접기/펼치기 컨트롤에 필수 — 스크린리더가 현재 상태를 알림
- `aria-haspopup="menu"`: 드롭다운 메뉴 트리거에 필수 — 메뉴 존재를 사전 알림
- `aria-describedby`: dialog에 설명 텍스트 연결 — 스크린리더가 용도를 설명
- `role="switch" + aria-checked`: 토글 컨트롤의 시맨틱 표준 패턴
- 조건부 렌더링 블록 내 ARIA 속성 추가는 항상 안전 (하이드레이션 에러 없음)

### 시각적 정합성 패턴 (Round 5에서 학습)
- `shadow-md shadow-primary/5`: 색조가 있는 그림자로 브랜드 일관성 유지
- `shadow-sm shadow-destructive/5`: 에러/경고 요소에 같은 패턴 적용
- 버튼 shadow 크기 통일: 같은 계층의 버튼은 같은 shadow 레벨 사용
- `animate-bounce`: 드래그앤드롭 같은 일시적 오버레이에 적합한 주의 환기 효과
- 조건부 렌더링 블록 내 CSS 클래스 변경은 항상 안전 (하이드레이션 에러 없음)

## keep된 변경 목록
1. icon-192.png PWA 아이콘 생성
2. workspaces API 빈 배열 반환
3. URL 입력 autofocus + 포커스 유지
5. 에러 메시지 role=alert + aria-live
6. 생성 버튼 disabled + 로딩 스피너
7. 사이드바 히스토리 접근성
11. URL 칩 삭제 버튼 hover 강화
13. 로딩 스켈레톤 aria-busy + aria-label
15. 설정 팝오버 ESC 닫기 + role=dialog
16. ViewModeSelector radiogroup
18. FilterBar type=search
19. 생성 버튼 영역 role=group
20. SettingsPopover aria-pressed
21. FilterBar+LoadingSkeleton memo
22. UrlInput memo + useCallback
23. handleGenerate/Merged/Fusion useCallback
24. Header memo + selector 분리
25. ScheduleModal/HelpPanel/GuidedTour 인라인 함수 제거
26. SettingsPopover 버튼 focus-visible 링
27. GenerationModeSelector radiogroup 접근성
28. FusionOptions role=group
29. 에이전트 모드 role=switch
30. ResultCard hover 트랜지션 강화
31. LoadingSkeleton 패딩/간격/shadow 개선
32. URL 칩 hover shadow + 삭제 버튼 scale
33. 생성 버튼 active:scale + hover:shadow-lg
34. SettingsPopover 버튼 active:scale-95
35. 히스토리 항목 활성 상태 border
36. ResultCard 접기/펼치기 aria-expanded
37. SettingsPopover 웹 검색 보강 role=switch
38. NlpAnalysisSection 접기/펼치기 aria-expanded
39. ResultCard 더보기 메뉴 aria-haspopup
40. SettingsPopover dialog aria-describedby
41. 활성 카드 shadow-md shadow-primary/5 깊이감
42. 에러 메시지 shadow-sm shadow-destructive/5
43. combined/fusion 버튼 shadow-md 통일
44. 드래그 오버레이 border/rounded-xl + bounce
45. 더 보기 버튼 hover:shadow-md active:scale
