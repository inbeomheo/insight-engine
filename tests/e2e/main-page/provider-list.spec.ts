import { test, expect } from '../fixtures/test-fixtures';
import type { Page } from '@playwright/test';

async function openSettingsPopoverIfNeeded(page: Page) {
  const providerSelect = page.locator('#provider');
  if (await providerSelect.isVisible()) {
    return providerSelect;
  }

  const settingsButton = page.locator('#settings-popover-btn');
  await expect(settingsButton).toBeVisible();
  await settingsButton.click();

  await expect(page.locator('#settings-popover')).toBeVisible();
  await expect(providerSelect).toBeVisible();
  return providerSelect;
}

test.describe('AI provider list @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('provider dropdown is visible', async ({ page }) => {
    const providerSelect = await openSettingsPopoverIfNeeded(page);
    await expect(providerSelect).toBeVisible();
  });

  test('has at least one provider option', async ({ page }) => {
    await openSettingsPopoverIfNeeded(page);
    const options = page.locator('#provider option');
    const count = await options.count();
    expect(count).toBeGreaterThan(0);
  });

  test('provider selection is possible', async ({ page }) => {
    const providerSelect = await openSettingsPopoverIfNeeded(page);

    const options = await providerSelect.locator('option').allTextContents();
    if (options.length > 1) {
      await providerSelect.selectOption({ index: 1 });
      const selectedValue = await providerSelect.inputValue();
      expect(selectedValue).toBeTruthy();
    }
  });
});
