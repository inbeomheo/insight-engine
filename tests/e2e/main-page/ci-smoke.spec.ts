import { test, expect } from '../fixtures/test-fixtures';

test.describe('CI smoke @no-auth', () => {
  test('frontend renders and backend health responds', async ({ page, request }) => {
    const health = await request.get('http://localhost:5001/health');
    expect(health.ok()).toBeTruthy();

    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto('/');
    await expect(page).toHaveTitle(/Insight Engine/i);
    await expect(page.getByText('Insight Engine').first()).toBeVisible();
    await expect(page.locator('#url-input')).toBeVisible();

    const criticalErrors = errors.filter(
      (error) => !error.includes('favicon') && !error.includes('manifest')
    );
    expect(criticalErrors).toHaveLength(0);
  });
});

