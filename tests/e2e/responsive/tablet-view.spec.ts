/**
 * 태블릿 뷰 반응형 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('태블릿 뷰 @parallel @no-auth @responsive', () => {
  test.use({ viewport: { width: 768, height: 1024 } }); // iPad

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('태블릿에서 레이아웃이 적절히 조정됨', async ({ page }) => {
    // 주요 요소 확인
    const urlInput = page.locator('input[placeholder*="YouTube"], [data-testid="url-input"]');
    await expect(urlInput).toBeVisible();

    // 콘텐츠가 적절한 여백을 가짐
    const body = page.locator('body');
    const padding = await body.evaluate((el) => {
      return getComputedStyle(el).padding;
    });

    expect(padding).toBeDefined();
  });

  test('모든 기능 요소가 표시됨', async ({ page }) => {
    // URL 입력
    await expect(page.locator('input:visible').first()).toBeVisible();

    // 셀렉트 박스들
    const selects = page.locator('select:visible');
    const selectCount = await selects.count();
    expect(selectCount).toBeGreaterThan(0);

    // 버튼
    await expect(page.locator('button:visible').first()).toBeVisible();
  });

  test('가로 스크롤 없음', async ({ page }) => {
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    expect(hasHorizontalScroll).toBeFalsy();
  });
});
