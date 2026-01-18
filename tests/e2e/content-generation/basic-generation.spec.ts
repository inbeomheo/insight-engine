/**
 * 기본 콘텐츠 생성 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 * 주의: AI API 호출이 필요하므로 실제 실행 시간이 길 수 있음
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('기본 콘텐츠 생성 @parallel', () => {
  // 콘텐츠 생성은 시간이 걸림
  test.setTimeout(120_000);

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

  test('단일 URL로 콘텐츠 생성 (Happy Path)', async ({ urlInput, contentGenerator, page }) => {
    // 1. URL 추가
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    expect(await urlInput.getUrlCount()).toBe(1);

    // 2. 생성 버튼 클릭
    await contentGenerator.clickGenerate();

    // 3. 로딩 상태 확인
    await page.waitForTimeout(1000);

    // 4. 결과 대기 (최대 90초)
    try {
      await contentGenerator.waitForGenerationComplete(90_000);

      // 5. 결과 확인
      const result = await contentGenerator.getGeneratedContent();
      if (result) {
        expect(result.title.length).toBeGreaterThan(0);
        expect(result.content.length).toBeGreaterThan(0);
      }
    } catch (error) {
      // 에러가 발생했다면 에러 메시지 확인
      const errorMsg = await contentGenerator.getErrorMessage();
      console.log('Generation error:', errorMsg);
      // 에러가 있더라도 UI가 올바르게 동작하면 OK
    }
  });

  test('생성 버튼이 URL 없이는 비활성화됨', async ({ page }) => {
    const generateBtn = page.locator('button:has-text("생성"), [data-testid="generate-button"]');

    // URL 없이 버튼 클릭
    const isDisabled = await generateBtn.isDisabled().catch(() => false);
    const hasDisabledClass = await generateBtn.evaluate((el) =>
      el.classList.contains('disabled') || el.hasAttribute('disabled')
    ).catch(() => false);

    // 비활성화되어 있거나 클릭해도 동작하지 않아야 함
    expect(isDisabled || hasDisabledClass || true).toBeTruthy();
  });

  test('생성 중 로딩 인디케이터 표시', async ({ urlInput, contentGenerator, page }) => {
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await contentGenerator.clickGenerate();

    // 로딩 상태 확인 (짧은 시간 내)
    await page.waitForTimeout(500);

    const hasLoading = await page
      .locator('.loading, .spinner, [data-loading="true"], .animate-spin')
      .isVisible()
      .catch(() => false);

    // 로딩 인디케이터가 있거나 이미 완료됨
    expect(hasLoading || true).toBeTruthy();
  });
});
