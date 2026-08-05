/**
 * 테마 테스트 (시스템 연동)
 *
 * 학습 엔진 UI 전환으로 수동 테마 전환 버튼(#theme-toggle-btn)은 제거됨.
 * 현재 테마는 next-themes(attribute="class", defaultTheme="system")가
 * OS의 prefers-color-scheme을 따라 html 클래스(light/dark)로 적용한다.
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('테마 (시스템 연동) @parallel @no-auth', () => {
  test('시스템 라이트 모드에서 light 테마가 적용됨', async ({ page, mainPage }) => {
    await page.emulateMedia({ colorScheme: 'light' });
    await mainPage.goto();

    const html = page.locator('html');
    await expect(html).toHaveClass(/light/);

    // next-themes가 color-scheme 스타일도 함께 적용
    const colorScheme = await page.evaluate(() => document.documentElement.style.colorScheme);
    expect(colorScheme).toBe('light');
  });

  test('시스템 다크 모드에서 dark 테마가 적용되고 배경색이 달라짐', async ({ page, mainPage }) => {
    await page.emulateMedia({ colorScheme: 'dark' });
    await mainPage.goto();

    const html = page.locator('html');
    await expect(html).toHaveClass(/dark/);

    const darkBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);

    // 라이트 모드로 전환하면 배경색이 실제로 달라져야 함
    await page.emulateMedia({ colorScheme: 'light' });
    await expect(html).toHaveClass(/light/);
    const lightBg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);

    expect(darkBg).not.toBe(lightBg);
  });

  test('시스템 테마 변경이 리로드 없이 실시간 반영됨', async ({ page, mainPage }) => {
    await page.emulateMedia({ colorScheme: 'light' });
    await mainPage.goto();

    const html = page.locator('html');
    await expect(html).toHaveClass(/light/);

    // OS 테마 변경 시뮬레이션 → 리로드 없이 dark 클래스로 전환
    await page.emulateMedia({ colorScheme: 'dark' });
    await expect(html).toHaveClass(/dark/);

    const colorScheme = await page.evaluate(() => document.documentElement.style.colorScheme);
    expect(colorScheme).toBe('dark');
  });
});
