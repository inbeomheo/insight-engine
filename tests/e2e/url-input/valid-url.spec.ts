/**
 * 유효한 URL 입력 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증: 불필요 (새 UI는 로그인 게이트 없음 — Supabase 비활성 환경)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('유효한 URL 입력 @parallel', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('유효한 YouTube URL 추가', async ({ page, urlInput }) => {
    const url = TEST_DATA.VALID_URLS[0];
    await urlInput.addUrl(url);

    const count = await urlInput.getUrlChipCount();
    expect(count).toBe(1);

    // 칩에 videoId가 표시됨 (모바일 셸의 전체 URL 텍스트와 구분 위해 exact)
    await expect(page.getByText('jNQXAC9IVRw', { exact: true })).toBeVisible();
  });

  test('짧은 URL (youtu.be) 추가', async ({ page, urlInput }) => {
    const url = 'https://youtu.be/dQw4w9WgXcQ';
    await urlInput.addUrl(url);

    const count = await urlInput.getUrlChipCount();
    expect(count).toBe(1);

    // youtu.be 형식도 videoId가 추출되어 칩에 표시됨
    await expect(page.getByText('dQw4w9WgXcQ', { exact: true })).toBeVisible();
  });

  test('여러 URL 추가', async ({ urlInput }) => {
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[2]);

    const count = await urlInput.getUrlChipCount();
    expect(count).toBe(3);
  });

  test('URL 추가 후 입력 필드 초기화', async ({ page, urlInput }) => {
    const input = page.locator('#url-input');
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);

    const inputValue = await input.inputValue();
    expect(inputValue).toBe('');
  });
});
