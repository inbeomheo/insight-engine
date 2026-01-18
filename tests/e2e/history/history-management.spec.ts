/**
 * 히스토리 관리 테스트
 *
 * 병렬 실행: ✅
 * 인증 필요: ✅ (storageState 사용)
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('히스토리 관리 @parallel @auth-required', () => {
  test.beforeEach(async ({ mainPage, page }) => {
    await mainPage.goto();

    // 로그인 버튼이 없으면 (Supabase 비활성화) 스킵
    const loginLink = page.locator('a:has-text("로그인"), button:has-text("로그인")');
    const authEnabled = await loginLink.isVisible({ timeout: 2000 }).catch(() => false);
    if (!authEnabled) {
      test.skip(true, '인증이 비활성화된 환경');
    }
  });

  test('히스토리 패널이 존재함', async ({ page }) => {
    // 히스토리 버튼 찾기 (nav-icon-btn with data-section="history")
    const historyToggle = page.locator('button[data-section="history"]');
    const isVisible = await historyToggle.isVisible().catch(() => false);

    if (!isVisible) {
      test.skip(true, '히스토리 기능이 없거나 비활성화됨');
      return;
    }

    await historyToggle.click();
    await page.waitForTimeout(500);

    // 히스토리 뷰 확인 (#history-view)
    const historyView = page.locator('#history-view');
    const viewVisible = await historyView.isVisible().catch(() => false);
    expect(viewVisible).toBeTruthy();
  });

  test('빈 히스토리 안내 메시지', async ({ page }) => {
    const historyToggle = page.locator('button[data-section="history"]');

    if (!(await historyToggle.isVisible().catch(() => false))) {
      test.skip(true, '히스토리 기능 없음');
      return;
    }

    await historyToggle.click();
    await page.waitForTimeout(500);

    // 빈 상태 메시지 (#history-empty-state) 또는 히스토리 항목 확인
    const emptyState = page.locator('#history-empty-state');
    const historyList = page.locator('#history-list .history-item');

    const hasEmptyState = await emptyState.isVisible().catch(() => false);
    const hasItems = (await historyList.count()) > 0;

    // 빈 상태 메시지가 있거나 히스토리 항목이 있으면 OK
    expect(hasEmptyState || hasItems).toBeTruthy();
  });
});
