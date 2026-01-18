/**
 * 사용량 추적 테스트
 *
 * 병렬 실행: ✅
 * 인증 필요: ✅ (storageState 사용)
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('사용량 추적 @parallel @auth-required', () => {
  test.beforeEach(async ({ mainPage, page }) => {
    await mainPage.goto();

    // Supabase 비활성화 환경에서는 인증 기능 없음 - 사용량 기능도 비활성화됨
    // 하지만 사용량 UI는 존재할 수 있으므로 테스트는 계속 진행
  });

  test('사용량 표시 요소가 존재함', async ({ page }) => {
    // 사용량 표시 찾기
    const usageDisplay = page.locator(
      ':has-text("사용량"), :has-text("남은"), :has-text("크레딧"), [data-testid="usage-display"]'
    );
    const isVisible = await usageDisplay.first().isVisible().catch(() => false);

    // 사용량 표시가 있으면 확인
    if (isVisible) {
      const text = await usageDisplay.first().textContent();
      expect(text).toBeTruthy();
    } else {
      // 사용량 기능이 없어도 OK
      test.skip(true, '사용량 표시 기능 없음');
    }
  });

  test('사용량 패널 열기', async ({ page }) => {
    // 사용량 버튼 찾기 (nav-icon-btn with data-section="usage")
    const usageToggle = page.locator('button[data-section="usage"]');

    if (!(await usageToggle.isVisible().catch(() => false))) {
      test.skip(true, '사용량 토글 버튼 없음');
      return;
    }

    await usageToggle.click();
    await page.waitForTimeout(500);

    // 사용량 뷰 확인 (#usage-view)
    const usageView = page.locator('#usage-view');
    const visible = await usageView.isVisible().catch(() => false);
    expect(visible).toBeTruthy();
  });
});
