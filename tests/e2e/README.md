# Insight Engine E2E 테스트

Playwright 기반 E2E 테스트로, **최대 병렬 실행**에 최적화되어 있습니다.

## 병렬 테스트 구조

```
tests/e2e/
├── playwright.config.ts     # 병렬 실행 설정
├── fixtures/
│   └── test-fixtures.ts     # 공통 헬퍼 및 데이터
├── .auth/
│   └── user.json           # 인증 상태 (자동 생성)
├── seeds/                   # 테스트 초기화 파일
│
├── main-page/              # 🔵 인증 불필요 (완전 병렬)
├── url-input/              # 🔵 인증 불필요 (완전 병렬)
├── batch-generation/       # 🔵 인증 불필요 (완전 병렬)
├── accessibility/          # 🔵 인증 불필요 (완전 병렬)
├── responsive/             # 🔵 인증 불필요 (완전 병렬)
├── error-handling/         # 🔵 인증 불필요 (완전 병렬)
├── performance/            # 🔵 인증 불필요 (완전 병렬)
│
├── auth/                   # 🟡 인증 테스트
│   └── setup.spec.ts       #    → 의존성 테스트 (먼저 실행)
├── settings/               # 🟠 인증 필요 (setup 후 실행)
├── history/                # 🟠 인증 필요 (setup 후 실행)
└── usage/                  # 🟠 인증 필요 (setup 후 실행)
```

## 빠른 시작

```bash
# 1. 의존성 설치
cd tests/e2e
npm install
npx playwright install

# 2. 테스트 실행 (병렬)
npm test

# 3. UI 모드로 실행 (디버깅)
npm run test:ui
```

## 병렬 실행 명령어

### 전체 테스트 (자동 병렬)
```bash
npm test                    # 모든 테스트 병렬 실행
npm run test:parallel       # 명시적 병렬 (workers=auto)
```

### 카테고리별 실행 (동시에 여러 카테고리 가능)
```bash
npm run test:no-auth        # 인증 불필요 테스트만
npm run test:content        # 콘텐츠 생성 테스트만
npm run test:batch          # 배치 처리 테스트만
npm run test:auth           # 인증 관련 테스트
npm run test:a11y           # 접근성 테스트
npm run test:responsive     # 반응형 테스트
npm run test:performance    # 성능 테스트
```

### 크로스 브라우저 / 모바일
```bash
npm run test:cross-browser  # Chrome, Firefox, Safari
npm run test:mobile         # 모바일 (Pixel 5, iPhone 13)
```

### CI/CD 환경
```bash
npm run test:ci             # 4 workers, 2 retries

# Sharding (여러 머신에 분산)
npm run test:shard 1/4      # 첫 번째 머신
npm run test:shard 2/4      # 두 번째 머신
npm run test:shard 3/4      # 세 번째 머신
npm run test:shard 4/4      # 네 번째 머신
```

## 병렬 테스트 원칙

### 1. 테스트 격리
각 테스트는 독립적으로 실행됩니다:
- 다른 테스트의 결과에 의존하지 않음
- 자체 브라우저 컨텍스트 사용
- 테스트 데이터를 공유하지 않음

### 2. 상태 관리
```typescript
// ❌ Bad: 전역 상태 사용
let sharedData = {};

// ✅ Good: 테스트별 독립 데이터
test('example', async ({ page }) => {
  const testData = { ... };
});
```

### 3. 인증 상태 재사용
인증이 필요한 테스트는 `storageState`를 사용:
```typescript
// playwright.config.ts
{
  name: 'authenticated-tests',
  dependencies: ['auth-setup'],  // setup 먼저 실행
  use: {
    storageState: '.auth/user.json',  // 상태 재사용
  },
}
```

## 테스트 추가 가이드

### 인증 불필요 테스트 추가
```typescript
// tests/e2e/new-category/new-test.spec.ts
import { test, expect } from '../fixtures/test-fixtures';

test.describe('새 테스트 @parallel @no-auth', () => {
  test('테스트 케이스', async ({ page, mainPage }) => {
    await mainPage.goto();
    // 테스트 로직
  });
});
```

### 인증 필요 테스트 추가
`playwright.config.ts`의 `authenticated-tests` 프로젝트에 경로 추가:
```typescript
testMatch: [
  '**/auth/!(setup)*.spec.ts',
  '**/settings/**/*.spec.ts',
  '**/new-auth-category/**/*.spec.ts',  // 추가
],
```

## 성능 최적화

### 워커 수 조절
```bash
# CPU 코어에 맞게 자동
npx playwright test --workers=auto

# 수동 지정
npx playwright test --workers=8
```

### 특정 테스트만 실행
```bash
# 파일 지정
npx playwright test main-page/

# 패턴 매칭
npx playwright test -g "로그인"

# 태그 필터
npx playwright test --grep "@no-auth"
```

## 리포트 확인

```bash
# HTML 리포트 열기
npm run report

# JSON 결과 확인
cat tests/test-results/results.json
```
