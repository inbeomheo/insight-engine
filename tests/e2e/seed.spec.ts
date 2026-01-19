import { test, expect } from '@playwright/test';

test.describe('Seed Test', () => {
  test('seed - navigate to app', async ({ page }) => {
    await page.goto('http://localhost:5001');
    await expect(page).toHaveTitle(/Insight Engine/);
  });
});
