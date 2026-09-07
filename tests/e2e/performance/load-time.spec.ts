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

    // 주요 요소 대기 — 'input, button' 첫 매치는 숨겨진 MobileAppShell 버튼이라
    // 데스크톱에서 영원히 visible이 되지 않음 → 메인 URL 입력 필드 기준으로 대기
    await page.locator('#url-input').waitFor({ state: 'visible', timeout: 2000 });

    const renderTime = Date.now() - startTime;
    console.log(`First Input Visible: ${renderTime}ms`);

    expect(renderTime).toBeLessThan(2000);
  });

  test('반복 로드 후 회수된 힙 사용량이 16MB 이상 증가하지 않는다', async ({ page }) => {
    const client = await page.context().newCDPSession(page);
    await client.send('Performance.enable');
    const heapSizes: number[] = [];
    for (let i = 0; i < 3; i++) {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await client.send('HeapProfiler.collectGarbage');
      const { metrics } = await client.send('Performance.getMetrics');
      const heap = metrics.find((metric) => metric.name === 'JSHeapUsedSize');
      expect(heap).toBeDefined();
      heapSizes.push(heap!.value);
    }
    expect(heapSizes[2] - heapSizes[0]).toBeLessThan(16 * 1024 * 1024);
    await client.detach();
  });
});
