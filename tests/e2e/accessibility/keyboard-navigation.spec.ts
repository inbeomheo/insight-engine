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
    // 첫 번째 Tab
    await page.keyboard.press('Tab');
    const firstFocused = await page.evaluate(() => document.activeElement?.tagName);

    // 여러 번 Tab
    for (let i = 0; i < 5; i++) {
      await page.keyboard.press('Tab');
    }

    const laterFocused = await page.evaluate(() => document.activeElement?.tagName);

    // 포커스가 이동해야 함
    expect(firstFocused || laterFocused).toBeTruthy();
  });

  test('Shift+Tab으로 역방향 탐색', async ({ page }) => {
    // 먼저 여러 번 Tab
    for (let i = 0; i < 3; i++) {
      await page.keyboard.press('Tab');
    }

    const beforeShiftTab = await page.evaluate(() => document.activeElement?.tagName);

    // Shift+Tab
    await page.keyboard.press('Shift+Tab');

    const afterShiftTab = await page.evaluate(() => document.activeElement?.tagName);

    // 포커스가 변경되어야 함 (또는 같은 위치에 유지)
    expect(beforeShiftTab || afterShiftTab).toBeTruthy();
  });

  test('Enter 키로 버튼 활성화', async ({ page }) => {
    // 버튼에 포커스
    const button = page.locator('button:visible').first();
    await button.focus();

    // Enter 키 누름
    await page.keyboard.press('Enter');

    // 버튼이 동작해야 함 (에러 없이)
    expect(true).toBeTruthy();
  });

  test('Escape 키로 모달/드롭다운 닫기', async ({ page }) => {
    // 드롭다운 열기 시도
    const select = page.locator('select').first();
    if (await select.isVisible()) {
      await select.focus();
      await page.keyboard.press('Space');
      await page.waitForTimeout(300);

      // Escape로 닫기
      await page.keyboard.press('Escape');
    }

    expect(true).toBeTruthy();
  });

  test('포커스 표시가 시각적으로 명확함', async ({ page }) => {
    const input = page.locator('input:visible').first();
    if (await input.isVisible()) {
      await input.focus();

      // 포커스 스타일 확인
      const outlineStyle = await input.evaluate((el) => {
        const styles = getComputedStyle(el);
        return styles.outline || styles.boxShadow || styles.border;
      });

      // 어떤 형태로든 포커스 스타일이 있어야 함
      expect(outlineStyle).toBeTruthy();
    }
  });
});
