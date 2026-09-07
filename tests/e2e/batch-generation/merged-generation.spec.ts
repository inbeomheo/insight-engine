/**
 * 통합 생성 (Merged) 테스트
 *
 * - 2개 URL 통합 생성 → 통합 카드 (통합 뱃지) (API — CLIProxyAPI 필요)
 * - 통합 모드 CTA는 URL 2개 이상일 때만 활성화 (UI)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('통합 생성 (Merged)', () => {
  test.describe.configure({ timeout: 300_000 });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('2개 URL 통합 생성 → 통합 카드 (통합 뱃지)', async ({
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

    // "통합" 모드 선택
    await contentGenerator.selectMode('combined');

    // "통합 생성 ×2" CTA 클릭
    const generateBtn = page
      .getByRole('button', { name: /통합 생성/ })
      .filter({ visible: true })
      .first();
    await expect(generateBtn).toBeEnabled();
    await generateBtn.click();

    // 결과 대기
    await contentGenerator.waitForResult(280_000);

    // 결과 카드 1개 (통합)
    const resultCount = await contentGenerator.getResultCount();
    expect(resultCount).toBe(1);

    // "통합" 뱃지 확인 (카드 내부 스코프)
    const mergedBadge = page
      .locator('[data-report-id]')
      .first()
      .getByText('통합', { exact: true });
    await expect(mergedBadge).toBeVisible();
  });

  test('URL 1개일 때 통합 모드 CTA 비활성화 (2개 이상 필요)', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    // URL 1개만 추가 후 통합 모드 선택
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await contentGenerator.selectMode('combined');

    // 새 UI: 폴백 버튼 대신 '통합 생성' CTA가 표시되되 URL<2면 비활성화
    const combinedCta = page
      .getByRole('button', { name: /통합 생성/ })
      .filter({ visible: true })
      .first();
    await expect(combinedCta).toBeVisible();
    await expect(combinedCta).toBeDisabled();

    // URL 2개가 되면 활성화
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await expect(combinedCta).toBeEnabled();

    // 다시 1개로 줄이면 비활성화
    await urlInput.removeUrlByIndex(0);
    await expect(combinedCta).toBeDisabled();
  });
});
