/**
 * 합쳐서 분석 테스트
 *
 * - 2개 URL 합쳐서 → 통합 카드 (통합 뱃지) (API)
 * - URL 1개일 때 개별 분석 폴백 (UI)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('합쳐서 분석 (Merged)', () => {
  test.describe.configure({ timeout: 300_000 });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('2개 URL 합쳐서 → 통합 카드 (통합 뱃지)', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    // 저비용 설정
    await contentGenerator.openSettings();
    await page.locator('button').filter({ hasText: '요약' }).first().click();
    await page.locator('button').filter({ hasText: '짧게' }).click();
    await contentGenerator.closeSettings();

    // URL 2개 추가
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);

    // "합쳐서 분석" 모드 선택
    await page.getByRole('button', { name: '합쳐서 분석' }).first().click();

    // "합쳐서 분석" 실행 버튼 클릭
    const generateBtn = page.getByRole('button', { name: /합쳐서 분석/ }).last();
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // 결과 대기
    await contentGenerator.waitForResult(280_000);

    // 결과 카드 1개 (통합)
    const resultCount = await contentGenerator.getResultCount();
    expect(resultCount).toBe(1);

    // "통합" 뱃지 확인
    const mergedBadge = page.locator('[data-report-id]').first().getByText('통합');
    await expect(mergedBadge).toBeVisible();
  });

  test('URL 1개일 때 합쳐서 모드에서 개별 분석 폴백', async ({
    page,
    urlInput,
  }) => {
    // URL 1개만 추가
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);

    // URL 1개면 모드 선택기가 표시되지 않음
    const combinedMode = page.getByRole('button', { name: '합쳐서 분석' });
    await expect(combinedMode).not.toBeVisible();

    // 대신 "1개 URL 분석 시작" 버튼만 표시
    const singleBtn = page.getByRole('button', { name: /1개 URL 분석 시작/ });
    await expect(singleBtn).toBeVisible();
  });
});
