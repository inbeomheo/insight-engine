/**
 * AI 프로바이더 목록 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('AI 프로바이더 목록 @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('프로바이더 드롭다운이 표시됨', async ({ page }) => {
    const providerSelect = page.locator('#provider');
    await expect(providerSelect).toBeVisible();
  });

  test('최소 1개 이상의 프로바이더 옵션이 있음', async ({ page }) => {
    const options = page.locator('#provider option');
    const count = await options.count();
    expect(count).toBeGreaterThan(0);
  });

  test('프로바이더 선택이 가능함', async ({ page }) => {
    const providerSelect = page.locator('#provider');

    if (await providerSelect.isVisible()) {
      // 첫 번째 옵션 외의 다른 옵션 선택
      const options = await providerSelect.locator('option').allTextContents();
      if (options.length > 1) {
        await providerSelect.selectOption({ index: 1 });
        const selectedValue = await providerSelect.inputValue();
        expect(selectedValue).toBeTruthy();
      }
    }
  });
});
