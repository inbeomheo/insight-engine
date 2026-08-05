/**
 * URL 관리 테스트 (삭제, 최대 개수 제한)
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증: 불필요 (새 UI는 로그인 게이트 없음 — Supabase 비활성 환경)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('URL 관리 @parallel', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('URL 삭제', async ({ urlInput }) => {
    // 3개 URL 추가
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[2]);

    expect(await urlInput.getUrlChipCount()).toBe(3);

    // 첫 번째 URL 삭제
    await urlInput.removeUrlByIndex(0);

    expect(await urlInput.getUrlChipCount()).toBe(2);
  });

  test('모든 URL 삭제', async ({ urlInput }) => {
    await urlInput.addMultipleUrls(TEST_DATA.VALID_URLS.slice(0, 3));
    expect(await urlInput.getUrlChipCount()).toBe(3);

    // 칩 제거 버튼을 하나씩 눌러 전부 삭제 (새 UI에는 전체 삭제 버튼 없음)
    for (let i = 0; i < 3; i++) {
      await urlInput.removeUrlByIndex(0);
    }
    expect(await urlInput.getUrlChipCount()).toBe(0);
  });

  test('최대 10개 URL 제한', async ({ page, urlInput }) => {
    // 10개 URL 추가
    for (let i = 0; i < 10; i++) {
      await urlInput.addUrl(`https://www.youtube.com/watch?v=test${i}`);
    }

    expect(await urlInput.getUrlChipCount()).toBe(10);

    // 11번째 URL 추가 시도 → 거부 + 에러 메시지
    await urlInput.addUrl('https://www.youtube.com/watch?v=test10');

    await expect(page.getByText(/최대 10개/)).toBeVisible();
    expect(await urlInput.getUrlChipCount()).toBe(10);
  });
});
