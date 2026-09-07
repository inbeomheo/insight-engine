import { test, expect, injectReports, makeMockReport } from '../fixtures/test-fixtures';

test.describe('로컬 사용량 집계 @parallel @no-auth', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('빈 브라우저의 생성 결과와 누적 토큰은 0이다', async ({ page }) => {
    await injectReports(page, []);
    await page.goto('/dashboard');
    await expect(page.getByRole('heading', { name: '내 작업 요약', exact: true })).toBeVisible();
    const metric = (label: string) => page.locator('[data-slot="card"]')
      .filter({ has: page.locator('[data-slot="card-title"]').getByText(label, { exact: true }) })
      .locator('[data-slot="card-content"]');
    await expect(metric('저장된 결과')).toHaveText('0개');
    await expect(metric('누적 토큰')).toHaveText('0');
    await expect(metric('평균 길이')).toHaveText('0자');
    await expect(metric('저장 공간')).toHaveText('0/20');
    await expect(page.getByText('홈에서 URL이나 텍스트를 생성하면 여기에 쌓입니다.', { exact: true })).toBeVisible();
  });

  test('저장된 결과에서 토큰·길이·저장 공간을 합산하고 최근 결과에 연결한다', async ({ page }) => {
    await injectReports(page, [
      makeMockReport({ id: 'usage-latest', title: '최근 사용량 결과', content: '가'.repeat(120), usage: { total_tokens: 1200 }, createdAt: Date.now() }),
      makeMockReport({ id: 'usage-earlier', title: '이전 사용량 결과', content: '나'.repeat(80), usage: { total_tokens: 300 }, createdAt: Date.now() - 1000 }),
    ]);
    await page.goto('/dashboard');
    const metric = (label: string) => page.locator('[data-slot="card"]')
      .filter({ has: page.locator('[data-slot="card-title"]').getByText(label, { exact: true }) })
      .locator('[data-slot="card-content"]');
    await expect(metric('저장된 결과')).toHaveText('2개');
    await expect(metric('누적 토큰')).toHaveText('1,500');
    await expect(metric('평균 길이')).toHaveText('100자');
    await expect(metric('저장 공간')).toHaveText('2/20');
    await expect(page.getByText('여유 있음 · 10% 사용 중', { exact: true })).toBeVisible();
    const recent = page.locator('[data-slot="card"]')
      .filter({ has: page.locator('[data-slot="card-title"]').getByText('최근 로컬 결과', { exact: true }) });
    await expect(recent.getByRole('link')).toHaveCount(2);
    await expect(recent.getByRole('link').first()).toHaveAttribute('href', '/?report=usage-latest');
    await recent.getByRole('link').first().click();
    await expect(page).toHaveURL(/\?report=usage-latest$/);
    await expect(page.locator('[data-report-id="usage-latest"]')).toBeVisible();
  });
});
