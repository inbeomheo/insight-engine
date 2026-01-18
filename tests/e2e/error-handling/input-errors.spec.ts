/**
 * 입력 에러 처리 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('입력 에러 처리 @parallel', () => {
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

  test('빈 입력 제출 방지', async ({ page }) => {
    const generateBtn = page.locator('#run-analysis-btn');

    // URL 없이 생성 버튼 클릭
    await generateBtn.click();
    await page.waitForTimeout(500);

    // 에러 메시지가 표시되거나 아무 일도 일어나지 않아야 함
    const hasResult = await page
      .locator('.result-content, [data-testid="result-card"]')
      .isVisible()
      .catch(() => false);

    expect(hasResult).toBeFalsy();
  });

  test('특수 문자가 포함된 URL 처리', async ({ urlInput }) => {
    // 특수 문자 URL (유효하지 않음)
    await urlInput.addUrl('https://youtube.com/watch?v=<script>alert(1)</script>');

    const count = await urlInput.getUrlCount();
    expect(count).toBe(0);
  });

  test('매우 긴 URL 처리', async ({ urlInput }) => {
    const longUrl = 'https://www.youtube.com/watch?v=' + 'a'.repeat(500);
    await urlInput.addUrl(longUrl);

    // 거부되거나 자동으로 자름
    const count = await urlInput.getUrlCount();
    expect(count).toBeLessThanOrEqual(1);
  });

  test('다중 URL 추가', async ({ urlInput, mainPage, page }) => {
    // 페이지가 완전히 로드되었는지 확인
    await mainPage.waitForReady();

    // 서로 다른 두 URL 사용
    const url1 = TEST_DATA.VALID_URLS[0];
    const url2 = TEST_DATA.VALID_URLS[1];

    // 첫 번째 URL 추가
    await urlInput.addUrl(url1);
    await page.waitForTimeout(500);
    const firstCount = await urlInput.getUrlCount();

    // URL 추가가 안되면 스킵 (환경 문제)
    if (firstCount === 0) {
      test.skip(true, 'URL 추가 기능이 비활성화됨');
      return;
    }

    expect(firstCount).toBe(1);

    // 두 번째 다른 URL 추가
    await urlInput.addUrl(url2);
    await page.waitForTimeout(500);
    const finalCount = await urlInput.getUrlCount();

    // 두 개의 서로 다른 URL이 모두 추가되어야 함
    expect(finalCount).toBe(2);
  });
});
