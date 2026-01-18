import { defineConfig, devices } from '@playwright/test';

/**
 * Insight Engine E2E 테스트 설정
 *
 * 병렬 테스트 최적화:
 * - fullyParallel: true → 모든 테스트를 병렬 실행
 * - workers: 'auto' → CPU 코어 수에 맞게 워커 자동 조절
 * - 테스트 격리: 각 테스트가 독립적인 브라우저 컨텍스트 사용
 */
export default defineConfig({
  testDir: './',

  /* 병렬 실행 최대화 */
  fullyParallel: true,
  workers: process.env.CI ? 4 : undefined, // CI에서는 4개, 로컬은 자동 (CPU 코어 수)

  /* 실패 시 재시도 */
  retries: process.env.CI ? 2 : 0,

  /* 테스트 타임아웃 */
  timeout: 60_000, // 콘텐츠 생성에 시간이 걸릴 수 있음
  expect: {
    timeout: 10_000,
  },

  /* 리포터 설정 */
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: '../test-results/html-report' }],
    ['json', { outputFile: '../test-results/results.json' }],
  ],

  /* 전역 설정 */
  use: {
    baseURL: 'http://localhost:5001',

    /* 추적 및 디버깅 */
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    /* 타임아웃 */
    actionTimeout: 15_000,
    navigationTimeout: 30_000,

    /* 한국어 로케일 */
    locale: 'ko-KR',
    timezoneId: 'Asia/Seoul',
  },

  /* 테스트 프로젝트 - 병렬 실행 그룹 */
  projects: [
    // ========================================
    // 그룹 1: 인증 불필요 테스트 (완전 병렬)
    // ========================================
    {
      name: 'no-auth-chromium',
      testMatch: [
        '**/main-page/**/*.spec.ts',
        '**/url-input/**/*.spec.ts',
        '**/accessibility/**/*.spec.ts',
        '**/responsive/**/*.spec.ts',
        '**/auth/login.spec.ts', // 로그인 테스트는 인증 없이 실행
      ],
      use: {
        ...devices['Desktop Chrome'],
        storageState: undefined, // 인증 없음
      },
    },

    // ========================================
    // 그룹 2: 콘텐츠 생성 테스트 (병렬, 독립적)
    // ========================================
    {
      name: 'content-generation',
      testMatch: '**/content-generation/**/*.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        storageState: undefined,
      },
    },

    // ========================================
    // 그룹 3: 배치 처리 테스트 (병렬, 독립적)
    // ========================================
    {
      name: 'batch-generation',
      testMatch: '**/batch-generation/**/*.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        storageState: undefined,
      },
    },

    // ========================================
    // 그룹 4: 인증 필요 테스트 (Setup 후 실행)
    // ========================================
    {
      name: 'auth-setup',
      testMatch: '**/auth/setup.spec.ts',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'authenticated-tests',
      testMatch: [
        '**/settings/**/*.spec.ts',
        '**/history/**/*.spec.ts',
        '**/usage/**/*.spec.ts',
      ],
      dependencies: ['auth-setup'],
      use: {
        ...devices['Desktop Chrome'],
        storageState: '.auth/user.json',
      },
    },

    // ========================================
    // 그룹 5: 에러 및 엣지 케이스 (병렬)
    // ========================================
    {
      name: 'error-handling',
      testMatch: '**/error-handling/**/*.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        storageState: undefined,
      },
    },

    // ========================================
    // 그룹 6: 성능 테스트 (별도 실행)
    // ========================================
    {
      name: 'performance',
      testMatch: '**/performance/**/*.spec.ts',
      use: {
        ...devices['Desktop Chrome'],
        storageState: undefined,
      },
    },

    // ========================================
    // 크로스 브라우저 테스트 (선택적 - 브라우저 설치 필요)
    // 활성화: CROSS_BROWSER=true npx playwright test
    // ========================================
    ...(process.env.CROSS_BROWSER
      ? [
          {
            name: 'firefox',
            testMatch: '**/main-page/**/*.spec.ts',
            use: { ...devices['Desktop Firefox'] },
          },
          {
            name: 'webkit',
            testMatch: '**/main-page/**/*.spec.ts',
            use: { ...devices['Desktop Safari'] },
          },
        ]
      : []),

    // ========================================
    // 모바일 테스트 (반응형) - Chromium 에뮬레이션만 사용
    // ========================================
    {
      name: 'mobile-chrome',
      testMatch: '**/responsive/**/*.spec.ts',
      use: { ...devices['Pixel 5'] },
    },
    // mobile-safari는 WebKit 필요 - CROSS_BROWSER 모드에서만 활성화
    ...(process.env.CROSS_BROWSER
      ? [
          {
            name: 'mobile-safari',
            testMatch: '**/responsive/**/*.spec.ts',
            use: { ...devices['iPhone 13'] },
          },
        ]
      : []),
  ],

  /* 테스트 서버 자동 실행 */
  webServer: {
    command: 'python app.py',
    url: 'http://localhost:5001',
    cwd: '../../', // 프로젝트 루트 디렉토리
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    // 테스트 시 Supabase 인증 비활성화 (로그인 없이 모든 기능 사용)
    env: {
      ...process.env,
      SUPABASE_URL: '',
      SUPABASE_ANON_KEY: '',
    },
  },
});
