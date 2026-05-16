import { test, expect } from '../fixtures/test-fixtures';

test.describe('main page smoke @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('page title is rendered', async ({ page }) => {
    await expect(page).toHaveTitle(/Insight Engine/i);
  });

  test('primary shell UI is visible', async ({ page }) => {
    await expect(page.getByText('Insight Engine').first()).toBeVisible();
    await expect(page.locator('#url-input')).toBeVisible();
    await expect(page.locator('#settings-open-btn')).toBeVisible();
  });

  test('has no critical JavaScript console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    const criticalErrors = errors.filter(
      (error) => !error.includes('favicon') && !error.includes('manifest')
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test('page loads within 5 seconds', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    expect(Date.now() - startTime).toBeLessThan(5000);
  });
});
