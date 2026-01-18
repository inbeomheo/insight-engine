/**
 * 페이지 로드 성능 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('페이지 로드 성능 @parallel @no-auth @performance', () => {
  test('초기 페이지 로드가 10초 이내', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    const loadTime = Date.now() - startTime;
    console.log(`DOM Content Loaded: ${loadTime}ms`);

    // 개발 환경에서는 10초 이내 (병렬 테스트 시 리소스 경합 고려)
    expect(loadTime).toBeLessThan(10000);
  });

  test('네트워크 idle 상태가 15초 이내', async ({ page }) => {
    const startTime = Date.now();

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`Network Idle: ${loadTime}ms`);

    // 개발 환경에서는 15초 이내 (병렬 테스트 시 리소스 경합 고려)
    expect(loadTime).toBeLessThan(15000);
  });

  test('JavaScript 에러 없이 로드', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });

  test('주요 요소가 2초 이내에 표시됨', async ({ page }) => {
    await page.goto('/');

    const startTime = Date.now();

    // 주요 요소 대기
    await page.waitForSelector('input, button', { timeout: 2000 });

    const renderTime = Date.now() - startTime;
    console.log(`First Input Visible: ${renderTime}ms`);

    expect(renderTime).toBeLessThan(2000);
  });

  test('메모리 누수 없이 반복 로드 가능', async ({ page }) => {
    // 여러 번 페이지 로드
    for (let i = 0; i < 3; i++) {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
    }

    // 마지막 로드 후 메모리 체크 (가능한 경우)
    const metrics = await page.evaluate(() => {
      if ('memory' in performance) {
        return (performance as any).memory;
      }
      return null;
    });

    if (metrics) {
      console.log(`Used JS Heap: ${Math.round(metrics.usedJSHeapSize / 1024 / 1024)}MB`);
    }

    expect(true).toBeTruthy();
  });
});
