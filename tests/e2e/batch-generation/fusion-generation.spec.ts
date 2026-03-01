/**
 * 퓨전 분석 테스트
 *
 * - 2개 URL 퓨전 → 퓨전 카드 (퓨전 뱃지) (API)
 * - 퓨전 옵션 토글 (UI)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('퓨전 분석 (Fusion)', () => {
  test.describe.configure({ timeout: 300_000 });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('2개 URL 퓨전 → 퓨전 카드 (퓨전 뱃지)', async ({
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

    // "퓨전 분석" 모드 선택
    await page.getByRole('button', { name: '퓨전 분석' }).first().click();

    // 퓨전 옵션 패널이 표시됨
    await expect(page.getByText('퓨전 옵션')).toBeVisible();

    // "퓨전 분석" 실행 버튼 클릭
    const generateBtn = page.getByRole('button', { name: /퓨전 분석/ }).last();
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // 결과 대기
    await contentGenerator.waitForResult(280_000);

    // 결과 카드 존재
    const resultCount = await contentGenerator.getResultCount();
    expect(resultCount).toBeGreaterThanOrEqual(1);

    // "퓨전" 뱃지 확인
    const fusionBadge = page.locator('[data-report-id]').first().getByText('퓨전');
    await expect(fusionBadge).toBeVisible();
  });

  test('퓨전 옵션 토글 (웹 리서치/댓글 심층 분석)', async ({
    page,
    urlInput,
  }) => {
    // URL 2개 추가 (퓨전 모드 활성화 필요)
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);

    // "퓨전 분석" 모드 선택
    await page.getByRole('button', { name: '퓨전 분석' }).first().click();

    // 퓨전 옵션 패널 표시
    await expect(page.getByText('퓨전 옵션')).toBeVisible();

    // 웹 리서치 체크박스
    const webResearch = page.getByRole('checkbox').first();
    await expect(webResearch).toBeVisible();
    await expect(page.getByText('웹 리서치')).toBeVisible();

    // 댓글 심층 분석 체크박스
    const deepComments = page.getByRole('checkbox').nth(1);
    await expect(deepComments).toBeVisible();
    await expect(page.getByText('댓글 심층 분석')).toBeVisible();

    // 토글 동작 확인
    const initialWebState = await webResearch.isChecked();
    await webResearch.click();
    const afterWebState = await webResearch.isChecked();
    expect(afterWebState).toBe(!initialWebState);

    // 안내 문구
    await expect(page.getByText('퓨전 분석은 2~5개 URL이 필요합니다')).toBeVisible();
  });
});
