/**
 * 유효한 URL 입력 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ✅ (로그인 필요 시 스킵)
 */
import { test, expect, TEST_DATA, getRandomUrl } from '../fixtures/test-fixtures';

test.describe('유효한 URL 입력 @parallel', () => {
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

  test('유효한 YouTube URL 추가', async ({ urlInput }) => {
    const url = TEST_DATA.VALID_URLS[0];
    await urlInput.addUrl(url);

    const count = await urlInput.getUrlCount();
    expect(count).toBe(1);
  });

  test('짧은 URL (youtu.be) 추가', async ({ urlInput }) => {
    const url = 'https://youtu.be/dQw4w9WgXcQ';
    await urlInput.addUrl(url);

    const count = await urlInput.getUrlCount();
    expect(count).toBe(1);
  });

  test('여러 URL 추가', async ({ urlInput }) => {
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[2]);

    const count = await urlInput.getUrlCount();
    expect(count).toBe(3);
  });

  test('URL 추가 후 입력 필드 초기화', async ({ page, urlInput }) => {
    const input = page.locator('input[placeholder*="YouTube"], [data-testid="url-input"]');
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);

    const inputValue = await input.inputValue();
    expect(inputValue).toBe('');
  });
});
