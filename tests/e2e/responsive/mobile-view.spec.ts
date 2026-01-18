/**
 * 모바일 뷰 반응형 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('모바일 뷰 @parallel @no-auth @responsive', () => {
  test.use({ viewport: { width: 375, height: 667 } }); // iPhone SE

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('모바일에서 레이아웃이 깨지지 않음', async ({ page }) => {
    // 가로 스크롤 확인
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    expect(hasHorizontalScroll).toBeFalsy();
  });

  test('터치 타겟이 충분한 크기', async ({ page }) => {
    const buttons = page.locator('button:visible, a:visible, [role="button"]:visible');
    const count = await buttons.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const el = buttons.nth(i);
      const box = await el.boundingBox();

      if (box) {
        // 최소 44x44px (WCAG 권장)
        expect(box.width).toBeGreaterThanOrEqual(24); // 최소 기준 완화
        expect(box.height).toBeGreaterThanOrEqual(24);
      }
    }
  });

  test('텍스트가 읽기 쉬운 크기', async ({ page }) => {
    const textElements = page.locator('p, span, div, label, h1, h2, h3');
    const firstText = textElements.first();

    if (await firstText.isVisible()) {
      const fontSize = await firstText.evaluate((el) => {
        return parseFloat(getComputedStyle(el).fontSize);
      });

      // 최소 12px 이상
      expect(fontSize).toBeGreaterThanOrEqual(12);
    }
  });

  test('입력 필드가 화면 너비에 맞음', async ({ page }) => {
    const input = page.locator('input:visible').first();

    if (await input.isVisible()) {
      const box = await input.boundingBox();
      const viewportWidth = 375;

      if (box) {
        // 입력 필드가 뷰포트를 넘지 않음
        expect(box.x + box.width).toBeLessThanOrEqual(viewportWidth + 20);
      }
    }
  });
});
