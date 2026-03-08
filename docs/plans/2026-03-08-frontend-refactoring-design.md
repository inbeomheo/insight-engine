# 프론트엔드 재사용성 리팩토링 설계

> 목적: 코드 정리 + 개발 속도 개선 + 버그 방지 (전부)
> 범위: 프론트엔드 우선 (백엔드는 별도 Phase)
> 접근법: Layered (레이어별 안전한 순서)

## 분석 결과

- 148개 컴포넌트 중 60개에 구조적 중복
- 16개 훅 중 11개에 패턴 불일치
- 예상 절감: ~1,180줄

## Phase 구조

### Phase 1: 공유 훅 추출 (신규 파일만, 기존 코드 미수정)

| 훅 | 역할 | 대체 대상 |
|---|---|---|
| `useDebouncedValue<T>(value, ms)` | 디바운스 값 | FilterBar, Sidebar 등 5+ 컴포넌트의 수동 debounce |
| `useApiCall<T>()` | try-catch + loading + toast 자동화 | settings 8개 컴포넌트의 fetch 보일러플레이트 |
| `useListManager<T>(initial)` | 배열 add/remove/update | MemoryManager 3회 반복, QaRulesEditor 등 |

파일: `hooks/useDebouncedValue.ts`, `hooks/useApiCall.ts`, `hooks/useListManager.ts`

### Phase 2: 스토어 정리

- `makeStorage<T>(key, fallback)` 팩토리 → storage.ts 20+ load/save 쌍 통합
- hydrate 패턴 통합 (requestIdleCallback 로직 1곳으로)
- **기존 export 시그니처 유지** → 호출부 변경 없음

파일: `lib/storage.ts`, `stores/resultStore.ts`, `stores/settingsStore.ts`

### Phase 3: API 레이어 중복 제거

- `request<T>()` FormData 지원 추가 → generateFromFile/Audio 80줄→10줄
- `requestBlob()` 헬퍼 → export 함수 4개 단순화

파일: `lib/api.ts`

### Phase 4: Input 컴포넌트 공통화

- `InputWrapper`: 공통 포커스 스타일 + 에러 3초 타임아웃
- `DropZone`: 드래그 영역 공유 컴포넌트

파일: `components/ui/InputWrapper.tsx` (신규), `components/ui/DropZone.tsx` (신규), UrlInput, TextInput, FileUpload, KnowledgeManager

### Phase 5: Settings 컴포넌트 리팩토링

Phase 1 훅들을 실제 적용:
- `useApiCall` → ProviderSetup, NotionConnect, ApiKeyManager 등 8개
- `useListManager` → MemoryManager, QaRulesEditor 등 4개
- `useDebouncedValue` → FilterBar, Sidebar

### Phase 6: Result 컴포넌트 (Context + props 드릴링 제거)

- `ReportContext` 생성 → ResultCard 46개 서브컴포넌트 props 정리
- 서브컴포넌트가 Context에서 필요한 필드만 구독

파일: `components/result/ReportContext.tsx` (신규), ResultCard + 서브컴포넌트 ~12개

### Phase 7: 모달/타입 정리

- 모달 상태 UIStore 통합 + `useModal(id)` 훅
- `lib/types.ts` → `lib/types/` 디렉토리 분할 (index.ts re-export로 경로 유지)

## 안전 원칙

- 매 Phase: `tsc --noEmit` + `next build` + 커밋
- export 시그니처 유지 → 호출부 호환성 보장
- Phase 1~3 기존 코드 최소 변경, Phase 4~7 본격 적용
