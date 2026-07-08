import { test, expect } from '../fixtures/test-fixtures';

test.describe('CI smoke @no-auth', () => {
  test('frontend renders and backend health responds', async ({ page, request }) => {
    const health = await request.get('http://127.0.0.1:5001/health');
    expect(health.ok()).toBeTruthy();

    await page.addInitScript(() => {
      localStorage.setItem('insight-engine-onboarding-done', 'true');
    });

    const errors: string[] = [];
    const blockedFirstPartyRequests: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    page.on('requestfailed', (failedRequest) => {
      const failure = failedRequest.failure()?.errorText ?? '';
      if (!failure.includes('net::ERR_NETWORK_ACCESS_DENIED')) return;
      const url = new URL(failedRequest.url());
      if (['localhost', '127.0.0.1'].includes(url.hostname)) {
        blockedFirstPartyRequests.push(failedRequest.url());
      }
    });

    await page.goto('/');
    await expect(page).toHaveTitle(/Insight Engine/i);
    await expect(page.getByRole('heading', { name: /어떤 자료를/ })).toBeVisible();
    await expect(page.locator('#url-input')).toBeVisible();
    expect(blockedFirstPartyRequests).toHaveLength(0);

    const criticalErrors = errors.filter(
      (error) =>
        !error.includes('favicon') &&
        !error.includes('manifest') &&
        !error.includes('net::ERR_NETWORK_ACCESS_DENIED')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});

