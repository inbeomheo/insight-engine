/**
 * 프로바이더 전환 테스트 (실제 API 호출)
 *
 * DeepSeek 프로바이더로 콘텐츠 생성 확인
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('프로바이더 전환', () => {
  test.describe.configure({ timeout: 180_000 });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  /** 팝오버에서 프로바이더 선택 (포탈 클릭으로 팝오버 닫힐 수 있음) */
  async function selectProviderInPopover(
    page: import('@playwright/test').Page,
    contentGenerator: Awaited<ReturnType<typeof import('../fixtures/test-fixtures').test['_']>['contentGenerator']>,
    providerPattern: RegExp,
  ): Promise<boolean> {
    await contentGenerator.openSettings();

    const providerTrigger = page.locator('[role="combobox"]').first();
    await providerTrigger.click();

    const option = page.getByRole('option', { name: providerPattern });
    const hasOption = await option.isVisible().catch(() => false);
    if (!hasOption) return false;

    await option.click();
    // 포탈 클릭으로 팝오버 닫힐 수 있음 — 다시 열기
    await page.waitForTimeout(300);
    return true;
  }

  /** 팝오버에서 저비용 설정 적용 (요약 + 짧게) */
  async function applyCheapSettings(
    page: import('@playwright/test').Page,
    contentGenerator: Awaited<ReturnType<typeof import('../fixtures/test-fixtures').test['_']>['contentGenerator']>,
  ) {
    // 팝오버가 닫혀있으면 다시 열기
    const aiModelLabel = page.getByText('AI 모델');
    if (!await aiModelLabel.isVisible().catch(() => false)) {
      await contentGenerator.openSettings();
    }

    await page.locator('button').filter({ hasText: '요약' }).first().click();
    await page.locator('button').filter({ hasText: '짧게' }).click();
    await contentGenerator.closeSettings();
  }

  test('DeepSeek Chat으로 생성', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    const hasDeepseek = await selectProviderInPopover(
      page, contentGenerator, /deepseek/i,
    );

    if (!hasDeepseek) {
      test.skip(true, 'DeepSeek 프로바이더가 설정되어 있지 않음');
      return;
    }

    await applyCheapSettings(page, contentGenerator);

    // URL 추가 + 생성
    await urlInput.addUrl(TEST_DATA.SHORT_VIDEO);
    await contentGenerator.clickGenerate();

    // 결과 대기
    await contentGenerator.waitForResult(160_000);

    const card = page.locator('[data-report-id]').first();
    await expect(card).toBeVisible();
    await expect(card.locator('h3')).not.toBeEmpty();
  });

  test('프로바이더 변경 후에도 생성 동작', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    await contentGenerator.openSettings();

    const providerTrigger = page.locator('[role="combobox"]').first();
    await providerTrigger.click();

    const options = page.getByRole('option');
    const count = await options.count();

    if (count < 2) {
      test.skip(true, '프로바이더가 2개 미만');
      return;
    }

    // 두 번째 프로바이더 선택
    await options.nth(1).click();
    await page.waitForTimeout(300);

    // 팝오버 재오픈 → 저비용 설정
    await applyCheapSettings(page, contentGenerator);

    // URL 추가 + 생성
    await urlInput.addUrl(TEST_DATA.SHORT_VIDEO);
    await contentGenerator.clickGenerate();

    // 결과 대기
    await contentGenerator.waitForResult(160_000);

    const resultCount = await contentGenerator.getResultCount();
    expect(resultCount).toBeGreaterThanOrEqual(1);
  });
});
