/**
 * 잘못된 URL 입력 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증: 불필요 (새 UI는 로그인 게이트 없음 — Supabase 비활성 환경)
 *
 * 새 검증 규칙(학습 엔진 전환): /^https?:\/\/.+/i 만 검사.
 * → YouTube 외 웹페이지/RSS/arXiv/Podcast URL도 전부 유효.
 * → 무효한 것은 스킴 없는 입력과 비 http(s) 스킴뿐.
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('잘못된 URL 입력 @parallel', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('잘못된 형식의 URL 거부', async ({ urlInput }) => {
    // 스킴 없음 / 스킴 없는 YouTube / ftp 스킴 — 전부 거부되어야 함
    for (const invalid of TEST_DATA.INVALID_URLS) {
      await urlInput.addUrl(invalid);
    }

    const count = await urlInput.getUrlChipCount();
    expect(count).toBe(0);
  });

  test('YouTube가 아닌 웹페이지 URL 허용 (새 검증 규칙)', async ({ page, urlInput }) => {
    // 구 UI에서는 거부됐지만, 학습 엔진 전환 후 모든 http(s) URL 허용
    await urlInput.addUrl('https://google.com');

    const count = await urlInput.getUrlChipCount();
    expect(count).toBe(1);

    // Web 소스로 감지되어 도메인 칩이 표시됨
    await expect(page.getByRole('button', { name: 'google.com 제거' })).toBeVisible();
  });

  test('Vimeo URL 허용 (Web 소스로 감지)', async ({ page, urlInput }) => {
    // 구 UI에서는 거부됐지만, 이제 일반 웹페이지로 허용
    await urlInput.addUrl('https://vimeo.com/123456789');

    const count = await urlInput.getUrlChipCount();
    expect(count).toBe(1);

    await expect(page.getByRole('button', { name: 'vimeo.com 제거' })).toBeVisible();
  });

  test('에러 메시지 표시', async ({ page, urlInput }) => {
    await urlInput.addUrl('invalid-url');

    // 무효 URL 에러 메시지가 표시됨
    await expect(page.getByText(TEST_DATA.INVALID_URL_ERROR)).toBeVisible();

    // URL 칩은 추가되지 않음
    const count = await urlInput.getUrlChipCount();
    expect(count).toBe(0);
  });
});
