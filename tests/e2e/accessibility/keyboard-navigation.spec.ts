/**
 * 키보드 네비게이션 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('키보드 네비게이션 @parallel @no-auth @a11y', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('Tab 키로 주요 요소 탐색 가능', async ({ page }) => {
    await page.locator('#url-input').focus();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: '생성 설정 열기' })).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: '생성 시작', exact: true })).toBeFocused();
  });

  test('Shift+Tab으로 역방향 탐색', async ({ page }) => {
    await page.getByRole('button', { name: '생성 설정 열기' }).focus();
    await page.keyboard.press('Shift+Tab');
    await expect(page.locator('#url-input')).toBeFocused();
  });

  test('Enter 키로 버튼 활성화', async ({ page }) => {
    const button = page.getByRole('button', { name: '설정 열기', exact: true });
    await button.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog', { name: '설정', exact: true })).toBeVisible();
  });

  test('Escape 키로 모달/드롭다운 닫기', async ({ page }) => {
    const button = page.getByRole('button', { name: '설정 열기', exact: true });
    await button.click();
    const dialog = page.getByRole('dialog', { name: '설정', exact: true });
    await expect(dialog).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
  });

  test('포커스 표시가 시각적으로 명확함', async ({ page }) => {
    await page.locator('#url-input').focus();
    await page.keyboard.press('Tab');
    const button = page.getByRole('button', { name: '생성 설정 열기' });
    await expect(button).toBeFocused();
    const hasFocusRing = await button.evaluate((el) => {
      const style = getComputedStyle(el);
      return (style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0)
        || (style.boxShadow !== 'none' && style.boxShadow !== '');
    });
    expect(hasFocusRing).toBe(true);
  });
});
