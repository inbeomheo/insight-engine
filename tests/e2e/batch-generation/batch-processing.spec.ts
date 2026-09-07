/**
 * 배치 (개별 생성) 테스트
 *
 * - 2개 URL 개별 생성 → 결과 카드 2개 (API — CLIProxyAPI 필요)
 * - 생성 모드 선택기(개별/통합/퓨전) 상시 표시 + 모드 전환 시 CTA 교체 (UI)
 * - 최대 10개 URL 제한 (UI)
 * - URL 칩 삭제 동작 (UI)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('배치 처리 (개별 생성)', () => {
  test.describe.configure({ timeout: 300_000 });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('2개 URL 개별 생성 → 결과 카드 2개', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    test.skip(
      process.env.E2E_LIVE_GENERATION !== '1',
      '실제 CLIProxyAPI/YouTube 연동은 E2E_LIVE_GENERATION=1에서만 실행',
    );
    // 설정: 저비용 프리셋 (CLIProxyAPI GPT-5.5 · 요약 · 짧게)
    await contentGenerator.applyCheapPreset();

    // URL 2개 추가
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);

    // 개별 모드 선택 (기본값이지만 명시)
    await contentGenerator.selectMode('individual');

    // "콘텐츠 생성 ×2" CTA 클릭
    const generateBtn = page
      .getByRole('button', { name: /콘텐츠 생성/ })
      .filter({ visible: true })
      .first();
    await expect(generateBtn).toBeEnabled();
    await generateBtn.click();

    // 결과 카드 2개 대기
    await page.locator('[data-report-id]').nth(1).waitFor({
      state: 'visible',
      timeout: 280_000,
    });

    const resultCount = await contentGenerator.getResultCount();
    expect(resultCount).toBeGreaterThanOrEqual(2);
  });

  test('생성 모드 선택기 상시 표시 + 모드 전환 시 CTA 교체', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    // 새 UI: 모드 버튼(개별/통합/퓨전)은 URL 개수와 무관하게 항상 표시
    for (const label of ['개별', '통합', '퓨전']) {
      const modeBtn = page
        .getByRole('button', { name: label, exact: true })
        .filter({ visible: true })
        .first();
      await expect(modeBtn).toBeVisible();
    }

    // 기본(개별) 모드: '콘텐츠 생성' CTA 표시, URL 0개면 비활성화
    const individualCta = page
      .getByRole('button', { name: /콘텐츠 생성/ })
      .filter({ visible: true })
      .first();
    await expect(individualCta).toBeVisible();
    await expect(individualCta).toBeDisabled();

    // URL 1개 추가 → 개별 CTA 활성화
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await expect(individualCta).toBeEnabled();

    // 통합 모드 전환 → CTA가 '통합 생성'으로 교체되고 '콘텐츠 생성' CTA는 사라짐
    await contentGenerator.selectMode('combined');
    const combinedCta = page
      .getByRole('button', { name: /통합 생성/ })
      .filter({ visible: true })
      .first();
    await expect(combinedCta).toBeVisible();
    await expect(
      page.getByRole('button', { name: /콘텐츠 생성/ }).filter({ visible: true }),
    ).toHaveCount(0);

    // 통합 모드는 URL 2개 이상 필요 → 1개면 비활성화, 2개면 활성화
    await expect(combinedCta).toBeDisabled();
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await expect(combinedCta).toBeEnabled();

    // 퓨전 모드 전환 → CTA가 '퓨전 분석'으로 교체
    await contentGenerator.selectMode('fusion');
    const fusionCta = page
      .getByRole('button', { name: /퓨전 분석/ })
      .filter({ visible: true })
      .first();
    await expect(fusionCta).toBeVisible();
    await expect(fusionCta).toBeEnabled();
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
