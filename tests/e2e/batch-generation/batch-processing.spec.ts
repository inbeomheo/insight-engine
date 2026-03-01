/**
 * 배치 (각각 분석) 테스트
 *
 * - 2개 URL 각각 분석 → 결과 카드 2개 (API)
 * - URL 2개 추가 시 모드 선택기 표시 (UI)
 * - 최대 10개 URL 제한 (UI)
 * - URL 칩 삭제 동작 (UI)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('배치 처리 (각각 분석)', () => {
  test.describe.configure({ timeout: 300_000 });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('2개 URL 각각 분석 → 결과 카드 2개', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    // 설정: 저비용 프리셋
    await contentGenerator.openSettings();
    await page.locator('button').filter({ hasText: '요약' }).first().click();
    await page.locator('button').filter({ hasText: '짧게' }).click();
    await contentGenerator.closeSettings();

    // URL 2개 추가
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);

    // 개별 분석 모드 선택 (기본값이지만 명시)
    const individualBtn = page.getByRole('button', { name: '개별 분석' });
    if (await individualBtn.isVisible().catch(() => false)) {
      await individualBtn.click();
    }

    // "2개 URL 각각 분석" 버튼 클릭
    const generateBtn = page.getByRole('button', { name: /각각 분석/ });
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // 결과 카드 2개 대기
    await page.locator('[data-report-id]').nth(1).waitFor({
      state: 'visible',
      timeout: 280_000,
    });

    const resultCount = await contentGenerator.getResultCount();
    expect(resultCount).toBeGreaterThanOrEqual(2);
  });

  test('URL 2개 추가 시 모드 선택기 표시', async ({ page, urlInput }) => {
    // URL 1개 → 모드 선택기 없음
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    const modeSelector = page.getByRole('button', { name: '개별 분석' });
    await expect(modeSelector).not.toBeVisible();

    // URL 2개 → 모드 선택기 표시
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await expect(modeSelector).toBeVisible();

    // 3가지 모드 버튼 존재
    await expect(page.getByRole('button', { name: '개별 분석' })).toBeVisible();
    await expect(page.getByRole('button', { name: '합쳐서 분석' })).toBeVisible();
    await expect(page.getByRole('button', { name: '퓨전 분석' })).toBeVisible();
  });

  test('최대 10개 URL 제한', async ({ page, urlInput }) => {
    // 11개 URL 추가 시도 (다른 videoId로)
    const urls = Array.from({ length: 11 }, (_, i) =>
      `https://www.youtube.com/watch?v=test${String(i).padStart(5, '0')}`
    );

    for (const url of urls) {
      await urlInput.addUrl(url);
    }

    const chipCount = await urlInput.getUrlChipCount();
    expect(chipCount).toBeLessThanOrEqual(10);
  });

  test('URL 칩 삭제 동작', async ({ page, urlInput }) => {
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    expect(await urlInput.getUrlChipCount()).toBe(2);

    // 첫 번째 칩 삭제
    await urlInput.removeUrlByIndex(0);
    expect(await urlInput.getUrlChipCount()).toBe(1);

    // 나머지 삭제
    await urlInput.removeUrlByIndex(0);
    expect(await urlInput.getUrlChipCount()).toBe(0);
  });
});
