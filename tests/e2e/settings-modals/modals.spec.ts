// spec: specs/03-settings-modals.plan.md
// seed: seed.spec.ts

/**
 * 설정 및 모달 테스트 (학습 엔진 UI 기준)
 *
 * - 온보딩: Radix Dialog '환영합니다!' — localStorage 'insight-engine-onboarding-done'으로 제어
 * - 설정 모달: 헤더 '설정 열기' 버튼 → Dialog '설정' (AI 서비스/스타일 메모리/캐시 관리)
 * - 생성 설정 팝오버: '생성 설정 열기' 버튼 → role=dialog '생성 설정' (모델/스타일/길이/문체)
 *   (구 커스텀 스타일 모달은 UI 진입점이 제거되어 현행 설정 표면인 팝오버로 대체 검증)
 *
 * 병렬 실행: ✅ (상태 공유 없음, localStorage 기반 격리)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

/** 온보딩 완료 여부 localStorage 키 (frontend/lib/constants.ts STORAGE_KEYS.ONBOARDING_DONE) */
const ONBOARDING_KEY = 'insight-engine-onboarding-done';

test.describe('온보딩 모달 @parallel @no-auth', () => {
  test('TC-1.1: 온보딩 모달 표시', async ({ page }) => {
    // 1. 앱 첫 방문 시 (localStorage 클리어)
    await page.goto('/');
    await page.evaluate((key) => {
      localStorage.removeItem(key);
    }, ONBOARDING_KEY);
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Expected: 온보딩 모달 자동 표시 (dynamic import라 여유 있게 대기)
    const modal = page.getByRole('dialog', { name: '환영합니다!' });
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Expected: 환영 메시지 및 안내 텍스트 (VisuallyHidden 중복 존재 → first)
    await expect(modal.getByRole('heading', { name: '환영합니다!' }).first()).toBeVisible();
    await expect(modal.getByText('YouTube 영상을 AI로 분석하여').first()).toBeVisible();

    // Expected: 시작하기 버튼 표시
    await expect(modal.getByRole('button', { name: '시작하기' })).toBeVisible();
  });

  test('TC-1.2: 온보딩 완료', async ({ page }) => {
    // Setup: 온보딩 모달 표시
    await page.goto('/');
    await page.evaluate((key) => {
      localStorage.removeItem(key);
    }, ONBOARDING_KEY);
    await page.reload();
    await page.waitForLoadState('networkidle');

    const modal = page.getByRole('dialog', { name: '환영합니다!' });
    await expect(modal).toBeVisible({ timeout: 10000 });

    // 1. 온보딩 모달에서 시작하기 버튼 클릭 (모델 로딩 전에는 disabled → 클릭이 자동 대기)
    await modal.getByRole('button', { name: '시작하기' }).click();

    // Expected: 모달 닫힘
    await expect(modal).toBeHidden({ timeout: 3000 });

    // Expected: localStorage에 완료 상태 저장 (makeStorage가 JSON 직렬화 → "true")
    const completed = await page.evaluate((key) => localStorage.getItem(key), ONBOARDING_KEY);
    expect(completed).toBe('true');
  });

  test('TC-1.3: 재방문 시 모달 미표시', async ({ page }) => {
    // 1. 온보딩 완료 후 페이지 새로고침
    await page.goto('/');
    await page.evaluate((key) => {
      localStorage.setItem(key, 'true');
    }, ONBOARDING_KEY);
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000); // 모달이 표시될 시간을 충분히 대기

    // Expected: 온보딩 모달 표시되지 않음
    const modal = page.getByRole('dialog', { name: '환영합니다!' });
    await expect(modal).toBeHidden();
  });
});

test.describe('설정 모달 @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('TC-2.1: 설정 모달 열기', async ({ page }) => {
    // 1. 헤더의 설정 버튼 클릭
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();

    // Expected: 설정 모달 표시 (Dialog 제목 '설정')
    const modal = page.getByRole('dialog', { name: '설정', exact: true });
    await expect(modal).toBeVisible({ timeout: 3000 });

    // Expected: AI 서비스 섹션 + 모델 선택 표시 (구 프로바이더 목록 대응)
    await expect(modal.getByRole('heading', { name: 'AI 서비스' })).toBeVisible();
    await expect(modal.getByRole('combobox', { name: 'AI 모델 선택' })).toBeVisible();
  });

  test('TC-2.2: AI 서비스 정보 표시', async ({ page }) => {
    // 1. 설정 모달 열기
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();

    const modal = page.getByRole('dialog', { name: '설정', exact: true });
    await expect(modal).toBeVisible({ timeout: 3000 });

    // Expected: 단일 AI 서비스(ChatMock) 안내 표시
    // (API 키는 서버 환경변수로 관리 → 모달에는 서비스 정보만 노출)
    await expect(modal.getByRole('group', { name: 'ChatMock 서비스 정보' })).toBeVisible();
    await expect(modal.getByText('단일 AI 서비스 사용 중')).toBeVisible();

    // Expected: 캐시 관리 섹션 표시
    await expect(modal.getByRole('button', { name: '전체 캐시 삭제' })).toBeVisible();
  });

  test('TC-2.3: 모달 외부 클릭 닫기', async ({ page }) => {
    // 1. 설정 모달 열기
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();

    const modal = page.getByRole('dialog', { name: '설정', exact: true });
    await expect(modal).toBeVisible({ timeout: 3000 });

    // 2. 모달 외부 (Radix 오버레이) 클릭
    await page.locator('[data-slot="dialog-overlay"]').click({ position: { x: 10, y: 10 } });

    // Expected: 모달 닫힘
    await expect(modal).toBeHidden({ timeout: 3000 });
  });

  test('TC-2.4: ESC 키로 닫기', async ({ page }) => {
    // 1. 설정 모달 열기
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();

    const modal = page.getByRole('dialog', { name: '설정', exact: true });
    await expect(modal).toBeVisible({ timeout: 3000 });

    // 2. ESC 키 누름
    await page.keyboard.press('Escape');

    // Expected: 모달 닫힘
    await expect(modal).toBeHidden({ timeout: 3000 });
  });
});

test.describe('생성 설정 팝오버 @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('TC-3.1: 생성 설정 팝오버 열기', async ({ page }) => {
    // 1. 입력 영역의 "생성 설정 열기" 버튼 클릭
    await page
      .getByRole('button', { name: '생성 설정 열기', exact: true })
      .filter({ visible: true })
      .first()
      .click();

    // Expected: 생성 설정 팝오버 표시 (role=dialog, aria-label '생성 설정')
    const popover = page.getByRole('dialog', { name: '생성 설정' });
    await expect(popover).toBeVisible({ timeout: 3000 });

    // Expected: AI 모델 선택 + 스타일 4종(요약/Q&A/퀴즈/리텐션 카드) 표시
    await expect(popover.getByRole('combobox', { name: 'AI 모델 선택' })).toBeVisible();
    await expect(popover.getByRole('button', { name: /^요약 스타일 선택/ })).toBeVisible();
    await expect(popover.getByRole('button', { name: /^Q&A 스타일 선택/ })).toBeVisible();
    await expect(popover.getByRole('button', { name: /^퀴즈 스타일 선택/ })).toBeVisible();
    await expect(popover.getByRole('button', { name: /^리텐션 카드 스타일 선택/ })).toBeVisible();
  });

  test('TC-3.2: 생성 설정 변경 유지', async ({ page }) => {
    // 1. 팝오버 열기
    await page
      .getByRole('button', { name: '생성 설정 열기', exact: true })
      .filter({ visible: true })
      .first()
      .click();

    const popover = page.getByRole('dialog', { name: '생성 설정' });
    await expect(popover).toBeVisible({ timeout: 3000 });

    // 2. 스타일 '퀴즈' 선택
    const quizButton = popover.getByRole('button', { name: /^퀴즈 스타일 선택/ });
    await quizButton.click();
    await expect(quizButton).toHaveAttribute('aria-pressed', 'true');

    // 3. 길이 '짧게' 선택
    const shortButton = popover.getByRole('button', { name: '짧게 길이 선택' });
    await shortButton.click();
    await expect(shortButton).toHaveAttribute('aria-pressed', 'true');

    // 4. 팝오버 닫았다가 다시 열기
    await page.keyboard.press('Escape');
    await expect(popover).toBeHidden({ timeout: 3000 });
    await page
      .getByRole('button', { name: '생성 설정 열기', exact: true })
      .filter({ visible: true })
      .first()
      .click();
    await expect(popover).toBeVisible({ timeout: 3000 });

    // Expected: 변경한 설정이 유지됨 (스토어에 저장)
    await expect(popover.getByRole('button', { name: /^퀴즈 스타일 선택/ })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
    await expect(popover.getByRole('button', { name: '짧게 길이 선택' })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
  });

  test('TC-3.3: 팝오버 외부 클릭 닫기', async ({ page }) => {
    // 1. 팝오버 열기
    await page
      .getByRole('button', { name: '생성 설정 열기', exact: true })
      .filter({ visible: true })
      .first()
      .click();

    const popover = page.getByRole('dialog', { name: '생성 설정' });
    await expect(popover).toBeVisible({ timeout: 3000 });

    // 2. 팝오버 바깥 영역(메인 헤딩) 클릭
    await page.getByRole('heading', { name: '어떤 자료를 콘텐츠로 만들까요?' }).click();

    // Expected: 팝오버 닫힘
    await expect(popover).toBeHidden({ timeout: 3000 });
  });
});

test.describe('모달 접근성 @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('TC-4.1: 포커스 트랩 - 설정 모달', async ({ page }) => {
    // 1. 모달 열기
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();

    const modal = page.getByRole('dialog', { name: '설정', exact: true });
    await expect(modal).toBeVisible({ timeout: 3000 });

    // 2. Tab 키로 포커스 순회
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);

    // Expected: 포커스가 모달 내부에만 유지됨 (Radix Dialog 포커스 트랩)
    const focusedInModal = await page.evaluate(() => {
      const content = document.querySelector('[data-slot="dialog-content"]');
      return content?.contains(document.activeElement) ?? false;
    });

    expect(focusedInModal).toBe(true);
  });

  test('TC-4.2: ARIA 속성 확인 - 온보딩 모달', async ({ page }) => {
    // 1. 온보딩 상태 초기화 후 모달 열기
    await page.evaluate((key) => {
      localStorage.removeItem(key);
    }, ONBOARDING_KEY);
    await page.reload();
    await page.waitForLoadState('networkidle');

    const modal = page.getByRole('dialog', { name: '환영합니다!' });
    await expect(modal).toBeVisible({ timeout: 10000 });

    // 2. ARIA 속성 검사: 제목/설명 연결 (DialogTitle/DialogDescription)
    await expect(modal).toHaveAttribute('aria-labelledby', /.+/);
    await expect(modal).toHaveAttribute('aria-describedby', /.+/);

    // 모달 내부의 주요 요소들이 접근 가능한지 확인
    await expect(modal.getByRole('button', { name: '시작하기' })).toBeVisible();
  });

  test('TC-4.3: ARIA 속성 확인 - 설정 모달', async ({ page }) => {
    // 1. 모달 열기
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();

    const modal = page.getByRole('dialog', { name: '설정', exact: true });
    await expect(modal).toBeVisible({ timeout: 3000 });

    // 2. ARIA 속성 검사: 제목/설명 연결
    await expect(modal).toHaveAttribute('aria-labelledby', /.+/);
    await expect(modal).toHaveAttribute('aria-describedby', /.+/);

    // 닫기 버튼 접근 가능 확인 (sr-only 'Close' 라벨)
    await expect(modal.getByRole('button', { name: 'Close' })).toBeVisible();
  });

  test('TC-4.4: 키보드 네비게이션 - 생성 설정 팝오버', async ({ page }) => {
    // 1. 팝오버 열기
    await page
      .getByRole('button', { name: '생성 설정 열기', exact: true })
      .filter({ visible: true })
      .first()
      .click();

    const popover = page.getByRole('dialog', { name: '생성 설정' });
    await expect(popover).toBeVisible({ timeout: 3000 });

    // 2. 스타일 버튼에 포커스 후 Space 키로 선택 (키보드 조작)
    const styleButton = popover.getByRole('button', { name: /^Q&A 스타일 선택/ });
    await styleButton.focus();
    await page.keyboard.press('Space');
    await expect(styleButton).toHaveAttribute('aria-pressed', 'true');

    // 3. ESC 키로 팝오버 닫기
    await page.keyboard.press('Escape');

    // Expected: 팝오버 닫힘
    await expect(popover).toBeHidden({ timeout: 3000 });
  });
});
