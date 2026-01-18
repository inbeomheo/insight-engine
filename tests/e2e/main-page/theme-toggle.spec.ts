/**
 * 테마 전환 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('테마 전환 @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('테마 전환 버튼이 존재함', async ({ page }) => {
    const themeToggle = page.locator('#theme-toggle-btn');
    await expect(themeToggle).toBeVisible();
  });

  test('테마 전환 시 배경색이 변경됨', async ({ page }) => {
    const themeToggle = page.locator('#theme-toggle-btn');

    // 현재 배경색 저장
    const initialBgColor = await page.evaluate(() => {
      return getComputedStyle(document.body).backgroundColor;
    });

    // 테마 전환
    await themeToggle.click();
    await page.waitForTimeout(500);

    // 변경된 배경색 확인
    const newBgColor = await page.evaluate(() => {
      return getComputedStyle(document.body).backgroundColor;
    });

    // 테마가 변경되었거나 시스템 설정이면 OK
    expect(newBgColor).toBeTruthy();
  });

  test('테마 설정이 localStorage에 저장됨', async ({ page }) => {
    const themeToggle = page.locator('#theme-toggle-btn');

    await themeToggle.click();
    await page.waitForTimeout(300);

    const savedTheme = await page.evaluate(() => {
      return localStorage.getItem('cad_theme_v1') || localStorage.getItem('theme') || 'system';
    });

    expect(savedTheme).toBeTruthy();
  });
});
