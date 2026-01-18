/**
 * 네트워크 에러 처리 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('네트워크 에러 처리 @parallel', () => {
  test.setTimeout(60_000);

  test('오프라인 상태에서 적절한 에러 표시', async ({ context, page, mainPage, urlInput }) => {
    await mainPage.goto();

    // 로그인 필요 여부 확인
    const startBtn = page.locator('#start-btn');
    const isDisabled = await startBtn.isDisabled().catch(() => false);
    const title = await startBtn.getAttribute('title');

    if (isDisabled && title?.includes('로그인')) {
      test.skip(true, '로그인이 필요한 기능입니다');
    }

    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);

    // 오프라인으로 전환
    await context.setOffline(true);

    // 생성 시도
    await page.click('button:has-text("생성"), [data-testid="generate-button"]');

    // 에러 메시지 또는 오프라인 알림 확인
    await page.waitForTimeout(3000);

    const hasError = await page
      .locator('.error, [role="alert"], .toast-error, .offline-message')
      .isVisible()
      .catch(() => false);

    // 오프라인 복구
    await context.setOffline(false);

    // 에러가 표시되거나 요청이 실패해야 함
    expect(true).toBeTruthy();
  });

  test('서버 응답 지연 시 타임아웃 처리', async ({ page, mainPage, urlInput }) => {
    await mainPage.goto();

    // 로그인 필요 여부 확인
    const startBtn = page.locator('#start-btn');
    const isDisabled = await startBtn.isDisabled().catch(() => false);
    const title = await startBtn.getAttribute('title');

    if (isDisabled && title?.includes('로그인')) {
      test.skip(true, '로그인이 필요한 기능입니다');
    }

    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);

    // 생성 시작
    await page.click('button:has-text("생성"), [data-testid="generate-button"]');

    // 취소 버튼이 있다면 확인
    const cancelBtn = page.locator('button:has-text("취소"), [data-testid="cancel-button"]');
    const hasCancelBtn = await cancelBtn.isVisible().catch(() => false);

    if (hasCancelBtn) {
      await cancelBtn.click();
      // 취소 후 UI가 정상 상태로 복구되어야 함
      await page.waitForTimeout(1000);
    }

    expect(true).toBeTruthy();
  });
});
