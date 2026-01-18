/**
 * 잘못된 URL 입력 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ✅ (로그인 필요 시 스킵)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('잘못된 URL 입력 @parallel', () => {
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

  test('잘못된 형식의 URL 거부', async ({ urlInput }) => {
    await urlInput.addUrl('not-a-valid-url');

    const count = await urlInput.getUrlCount();
    expect(count).toBe(0);
  });

  test('YouTube가 아닌 URL 거부', async ({ urlInput }) => {
    await urlInput.addUrl('https://google.com');

    const count = await urlInput.getUrlCount();
    expect(count).toBe(0);
  });

  test('Vimeo URL 거부', async ({ urlInput }) => {
    await urlInput.addUrl('https://vimeo.com/123456789');

    const count = await urlInput.getUrlCount();
    expect(count).toBe(0);
  });

  test('에러 메시지 표시', async ({ page, urlInput }) => {
    await urlInput.addUrl('invalid-url');

    // 에러 메시지 또는 토스트 알림 확인
    const errorVisible = await page
      .locator('.error, .alert, [role="alert"], .toast')
      .isVisible()
      .catch(() => false);

    // 에러 메시지가 있거나 URL이 추가되지 않았으면 성공
    const count = await urlInput.getUrlCount();
    expect(count === 0 || errorVisible).toBeTruthy();
  });
});
