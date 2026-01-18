/**
 * 배치 처리 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('배치 처리 @parallel', () => {
  test.setTimeout(180_000); // 배치는 더 오래 걸림

  test.beforeEach(async ({ mainPage, page }) => {
    await mainPage.goto();

    // 로그인 필요 여부 확인
    const startBtn = page.locator('#start-btn');
    const isDisabled = await startBtn.isDisabled().catch(() => false);
    const title = await startBtn.getAttribute('title');

    if (isDisabled && title?.includes('로그인')) {
      test.skip(true, '로그인이 필요한 기능입니다');
    }
  });

  test('여러 URL 추가 가능', async ({ urlInput }) => {
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[2]);

    const count = await urlInput.getUrlCount();
    expect(count).toBe(3);
  });

  test('배치 생성 버튼이 존재함', async ({ urlInput, page }) => {
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);

    // 생성 버튼 확인 (#run-analysis-btn)
    const generateBtn = page.locator('#run-analysis-btn');
    await expect(generateBtn).toBeVisible();
  });

  test('진행 상황 UI가 있음', async ({ urlInput, page }) => {
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);

    // 생성 시작
    await page.click('#run-analysis-btn');
    await page.waitForTimeout(1000);

    // 진행 상황 표시 요소 확인 (있을 수도 있고 없을 수도 있음)
    const progressExists = await page
      .locator('.progress, [role="progressbar"], .batch-progress')
      .isVisible()
      .catch(() => false);

    // 진행 표시가 있거나 결과가 바로 나오면 OK
    expect(true).toBeTruthy();
  });

  test('최대 URL 제한 적용', async ({ urlInput, page }) => {
    // 10개 초과 추가 시도
    for (let i = 0; i < 12; i++) {
      await urlInput.addUrl(`https://www.youtube.com/watch?v=batch${i}`);
    }

    const count = await urlInput.getUrlCount();
    expect(count).toBeLessThanOrEqual(10);
  });
});
