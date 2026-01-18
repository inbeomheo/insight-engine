/**
 * URL 관리 테스트 (삭제, 순서 변경)
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ✅ (로그인 필요 시 스킵)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('URL 관리 @parallel', () => {
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

  test('URL 삭제', async ({ urlInput }) => {
    // 3개 URL 추가
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[2]);

    expect(await urlInput.getUrlCount()).toBe(3);

    // 첫 번째 URL 삭제
    await urlInput.removeUrl(0);

    expect(await urlInput.getUrlCount()).toBe(2);
  });

  test('모든 URL 삭제', async ({ urlInput }) => {
    await urlInput.addMultipleUrls(TEST_DATA.VALID_URLS.slice(0, 3));
    expect(await urlInput.getUrlCount()).toBe(3);

    await urlInput.clearAllUrls();
    expect(await urlInput.getUrlCount()).toBe(0);
  });

  test('최대 10개 URL 제한', async ({ page, urlInput }) => {
    // 10개 URL 추가
    for (let i = 0; i < 10; i++) {
      await urlInput.addUrl(`https://www.youtube.com/watch?v=test${i}`);
    }

    const count = await urlInput.getUrlCount();
    expect(count).toBeLessThanOrEqual(10);

    // 11번째 URL 추가 시도
    await urlInput.addUrl('https://www.youtube.com/watch?v=test10');

    // 여전히 10개 이하
    const finalCount = await urlInput.getUrlCount();
    expect(finalCount).toBeLessThanOrEqual(10);
  });
});
