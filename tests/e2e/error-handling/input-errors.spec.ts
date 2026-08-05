/**
 * 입력 에러 처리 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('입력 에러 처리 @parallel', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('빈 입력 제출 방지', async ({ page, contentGenerator }) => {
    // URL 0개 → 생성 CTA는 보이지만 비활성화 상태 (제출 자체가 불가능)
    const generateBtn = page
      .getByRole('button', { name: /콘텐츠 생성/ })
      .filter({ visible: true })
      .first();
    await expect(generateBtn).toBeVisible();
    await expect(generateBtn).toBeDisabled();

    // 로딩/결과가 생기지 않아야 함
    expect(await contentGenerator.isLoading()).toBeFalsy();
    expect(await contentGenerator.getResultCount()).toBe(0);
  });

  test('특수 문자가 포함된 URL은 텍스트로 안전하게 추가된다(XSS 없음)', async ({ page, urlInput }) => {
    // 스크립트 태그가 실행되면 dialog가 뜸 → 감지용 리스너
    let dialogFired = false;
    page.on('dialog', async (dialog) => {
      dialogFired = true;
      await dialog.dismiss();
    });

    // https:// 스킴이 있으므로 현재 검증 규칙상 유효 — 칩으로 추가됨
    await urlInput.addUrl('https://youtube.com/watch?v=<script>alert(1)</script>');

    expect(await urlInput.getUrlChipCount()).toBe(1);
    // React 이스케이프로 스크립트는 실행되지 않아야 함
    expect(dialogFired).toBeFalsy();
  });

  test('매우 긴 URL 처리', async ({ urlInput }) => {
    const longUrl = 'https://www.youtube.com/watch?v=' + 'a'.repeat(500);
    await urlInput.addUrl(longUrl);

    // 유효한 http(s) URL이므로 크래시 없이 칩 1개로 추가됨 (칩 라벨은 CSS로 잘림)
    expect(await urlInput.getUrlChipCount()).toBe(1);
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
    expect(await urlInput.getUrlChipCount()).toBe(1);

    // 두 번째 다른 URL 추가
    await urlInput.addUrl(url2);
    await page.waitForTimeout(500);

    // 두 개의 서로 다른 URL이 모두 추가되어야 함
    expect(await urlInput.getUrlChipCount()).toBe(2);
  });
});
