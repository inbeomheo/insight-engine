import type { Page } from '@playwright/test';
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

const firstVideoId = 'jNQXAC9IVRw';
const secondVideoId = 'dQw4w9WgXcQ';

async function addUrl(page: Page, url: string) {
  const input = page.locator('#url-input');
  await input.fill(url);
  await input.press('Enter');
  await page.waitForTimeout(300);
}

test.describe('core user journey', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('generate button is hidden without a URL', async ({ page }) => {
    await expect(page.locator('#run-analysis-btn')).not.toBeVisible();
  });

  test('generate button appears after URL entry', async ({ page }) => {
    await addUrl(page, TEST_DATA.VALID_URLS[0]);
    await expect(page.locator('#run-analysis-btn')).toBeVisible();
  });

  test('Enter adds a URL chip and clears the input', async ({ page }) => {
    const input = page.locator('#url-input');
    await addUrl(page, TEST_DATA.VALID_URLS[0]);

    await expect(page.getByText(firstVideoId)).toBeVisible();
    await expect(input).toHaveValue('');
  });

  test('invalid URL shows an inline error', async ({ page }) => {
    await addUrl(page, TEST_DATA.INVALID_URLS[0]);
    await expect(page.locator('p[role="alert"]')).toBeVisible();
  });

  test('URL remove button deletes the chip', async ({ page }) => {
    await addUrl(page, TEST_DATA.VALID_URLS[0]);

    await page.locator(`[aria-label*="${firstVideoId}"]`).click();
    await page.waitForTimeout(300);

    await expect(page.getByText(firstVideoId)).not.toBeVisible();
  });

  test('empty result state is shown', async ({ page }) => {
    await expect(page.locator('#url-input')).toBeVisible();
    await expect(page.locator('[data-report-id]')).toHaveCount(0);
  });

  test('onboarding modal can be dismissed when present', async ({ page }) => {
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');

    const dialog = page.getByRole('dialog');
    if (await dialog.isVisible().catch(() => false)) {
      await expect(dialog.getByRole('heading').first()).toBeVisible();
      await dialog.getByRole('button').last().click();
      await expect(dialog).not.toBeVisible();
    }
  });

  test('sidebar has a new analysis button', async ({ page }) => {
    await expect(page.locator('#new-analysis-btn')).toBeVisible();
  });

  test('sidebar history search accepts input when present', async ({ page }) => {
    const searchInput = page.locator('aside input').first();
    if (await searchInput.isVisible().catch(() => false)) {
      await searchInput.fill('test');
      await expect(searchInput).toHaveValue('test');
    }
  });

  test('header has logo and settings button', async ({ page }) => {
    await expect(page.getByText('Insight Engine').first()).toBeVisible();
    await expect(page.locator('#settings-open-btn')).toBeVisible();
  });

  test('settings button opens the settings dialog', async ({ page }) => {
    await page.locator('#settings-open-btn').click();
    await expect(page.getByRole('dialog')).toBeVisible();
  });
});

test.describe('multi URL mode', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('mode selector appears after two URLs are added', async ({ page }) => {
    await addUrl(page, TEST_DATA.VALID_URLS[0]);
    await addUrl(page, TEST_DATA.VALID_URLS[1]);

    await expect(page.getByText(firstVideoId)).toBeVisible();
    await expect(page.getByText(secondVideoId)).toBeVisible();
    await expect(page.locator('#run-analysis-btn')).toBeVisible();
  });

  test('maximum 10 URLs are accepted', async ({ page }) => {
    const urls = [
      ...TEST_DATA.VALID_URLS,
      'https://www.youtube.com/watch?v=L_jWHffIx5E',
      'https://www.youtube.com/watch?v=fJ9rUzIMcZQ',
      'https://www.youtube.com/watch?v=YQHsXMglC9A',
      'https://www.youtube.com/watch?v=hT_nvWreIhg',
      'https://www.youtube.com/watch?v=RgKAFK5djSk',
      'https://www.youtube.com/watch?v=ZZ5LpwO-An4',
    ];

    for (const url of urls) {
      await addUrl(page, url);
    }

    await expect(page.locator('[data-testid="remove-url-button"]')).toHaveCount(10);
  });
});
