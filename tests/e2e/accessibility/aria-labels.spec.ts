/**
 * ARIA 레이블 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('ARIA 레이블 @parallel @no-auth @a11y', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('버튼에 접근 가능한 이름이 있음', async ({ page }) => {
    const buttons = page.locator('button:visible');
    const count = await buttons.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const button = buttons.nth(i);
      const accessibleName = await button.evaluate((el) => {
        return el.textContent?.trim() ||
          el.getAttribute('aria-label') ||
          el.getAttribute('title') ||
          el.querySelector('img')?.getAttribute('alt');
      });

      // 버튼에 접근 가능한 이름이 있어야 함
      expect(accessibleName).toBeTruthy();
    }
  });

  test('주요 입력 필드에 레이블이 있음', async ({ page }) => {
    // 주요 입력 필드만 확인 (URL 입력)
    const mainInput = page.locator('#url-input');
    const isVisible = await mainInput.isVisible().catch(() => false);

    if (isVisible) {
      const hasLabel = await mainInput.evaluate((el) => {
        const ariaLabel = el.getAttribute('aria-label');
        const ariaLabelledBy = el.getAttribute('aria-labelledby');
        const placeholder = el.getAttribute('placeholder');
        const title = el.getAttribute('title');
        const id = el.id;
        const label = id ? document.querySelector(`label[for="${id}"]`) : null;

        return !!(ariaLabel || ariaLabelledBy || label || placeholder || title);
      });

      // 주요 입력 필드에 최소한 placeholder나 label이 있어야 함
      expect(hasLabel).toBeTruthy();
    } else {
      // 메인 입력 필드가 없으면 다른 입력 필드 확인
      const anyInputHasLabel = await page.locator('input').first().evaluate((el) => {
        return !!(el.getAttribute('placeholder') || el.getAttribute('aria-label'));
      }).catch(() => true);

      expect(anyInputHasLabel).toBeTruthy();
    }
  });

  test('이미지에 alt 텍스트가 있음', async ({ page }) => {
    const images = page.locator('img:visible');
    const count = await images.count();

    for (let i = 0; i < Math.min(count, 5); i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      const role = await img.getAttribute('role');

      // alt가 있거나 role="presentation"으로 장식용임을 표시
      const isAccessible = alt !== null || role === 'presentation' || role === 'none';
      expect(isAccessible).toBeTruthy();
    }
  });

  test('랜드마크 영역이 정의됨', async ({ page }) => {
    // main, nav, header, footer 등 랜드마크 확인
    const hasMain = await page.locator('main, [role="main"]').count();
    const hasHeader = await page.locator('header, [role="banner"]').count();
    const hasNav = await page.locator('nav, [role="navigation"]').count();

    // 최소 하나의 랜드마크가 있어야 함
    expect(hasMain + hasHeader + hasNav).toBeGreaterThan(0);
  });
});
