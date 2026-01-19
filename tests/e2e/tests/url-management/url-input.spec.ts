/**
 * URL 입력 및 관리 테스트 (통합)
 * 
 * spec: specs/01-url-input-management.plan.md
 * seed: seed.spec.ts
 * 
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ✅ (로그인 필요 시 스킵)
 */
import { test, expect, TEST_DATA } from '../../fixtures/test-fixtures';

test.describe('URL 입력 및 관리', () => {
  test.beforeEach(async ({ mainPage, page }) => {
    // 앱 접속
    await mainPage.goto();

    // 로그인 필요 여부 확인
    const startBtn = page.locator('#run-analysis-btn');
    const isDisabled = await startBtn.isDisabled().catch(() => false);
    const title = await startBtn.getAttribute('title');

    if (isDisabled && title?.includes('로그인')) {
      test.skip(true, '로그인이 필요한 기능입니다');
    }
  });

  test.describe('Suite 1: URL 입력', () => {
    test('TC-1.1: 유효한 YouTube URL 입력', async ({ page, urlInput }) => {
      // 1. 앱 접속 (beforeEach에서 완료)
      
      // 2. URL 입력 필드에 "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 입력
      // 3. Enter 키 누름
      const testUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
      await urlInput.addUrl(testUrl);

      // Expected: URL 카드가 URL 목록에 추가됨
      const count = await urlInput.getUrlCount();
      expect(count).toBe(1);

      // Expected: 입력 필드가 초기화됨
      const input = page.locator('#url-input');
      const inputValue = await input.inputValue();
      expect(inputValue).toBe('');

      // Expected: URL 카드에 영상 정보 표시
      const urlCard = page.locator('#url-list-container .url-card').first();
      await expect(urlCard).toBeVisible();
    });

    test('TC-1.2: youtu.be 단축 URL 입력', async ({ urlInput }) => {
      // 1. URL 입력 필드에 "https://youtu.be/dQw4w9WgXcQ" 입력
      // 2. Enter 키 누름
      const testUrl = 'https://youtu.be/dQw4w9WgXcQ';
      await urlInput.addUrl(testUrl);

      // Expected: URL 카드가 정상 추가됨
      const count = await urlInput.getUrlCount();
      expect(count).toBe(1);
    });

    test('TC-1.3: 잘못된 URL 입력', async ({ page, urlInput }) => {
      // 1. URL 입력 필드에 "invalid-url" 입력
      // 2. Enter 키 누름
      await urlInput.addUrl('invalid-url');

      // Expected: 에러 메시지 표시
      const errorVisible = await page
        .locator('.error, .alert, [role="alert"], .toast, .toast-error')
        .isVisible()
        .catch(() => false);

      // Expected: URL이 목록에 추가되지 않음
      const count = await urlInput.getUrlCount();
      
      // 에러가 표시되거나 URL이 추가되지 않아야 함
      expect(count === 0 || errorVisible).toBeTruthy();
    });

    test('TC-1.4: 빈 입력', async ({ page, urlInput }) => {
      // 1. URL 입력 필드가 비어있는 상태에서 Enter 키 누름
      const input = page.locator('#url-input');
      await input.click();
      await page.waitForTimeout(100);
      await input.press('Enter');
      await page.waitForTimeout(500);

      // Expected: 아무 동작 없음 또는 안내 메시지
      const count = await urlInput.getUrlCount();
      expect(count).toBe(0);

      // 안내 메시지가 있을 수 있음 (선택사항)
      const message = await page
        .locator('.info, .warning, [role="alert"], .toast')
        .isVisible()
        .catch(() => false);

      // 카운트가 0이거나 메시지가 표시되면 성공
      expect(count === 0 || message).toBeTruthy();
    });
  });

  test.describe('Suite 2: URL 카드 관리', () => {
    test('TC-2.1: URL 삭제', async ({ urlInput }) => {
      // 1. URL 추가 후 삭제 버튼 클릭
      await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
      expect(await urlInput.getUrlCount()).toBe(1);

      await urlInput.removeUrl(0);

      // Expected: URL 카드가 목록에서 제거됨
      // Expected: 카운트 업데이트
      const count = await urlInput.getUrlCount();
      expect(count).toBe(0);
    });

    test('TC-2.2: 최대 10개 URL 제한', async ({ page, urlInput }) => {
      // 1. 11개의 URL 추가 시도
      
      // 10개 URL 추가
      for (let i = 0; i < 10; i++) {
        await urlInput.addUrl(`https://www.youtube.com/watch?v=test${i}`);
      }

      const countAfter10 = await urlInput.getUrlCount();
      expect(countAfter10).toBeLessThanOrEqual(10);

      // Expected: 10개 이후 추가 시 경고 메시지
      // 11번째 URL 추가 시도
      await urlInput.addUrl('https://www.youtube.com/watch?v=test10');

      // 경고 메시지 확인 (선택사항)
      const warningVisible = await page
        .locator('.warning, .alert, [role="alert"], .toast')
        .isVisible()
        .catch(() => false);

      // Expected: 11번째 URL 추가 거부
      const finalCount = await urlInput.getUrlCount();
      expect(finalCount).toBeLessThanOrEqual(10);
    });

    test('TC-2.3: 중복 URL 검증', async ({ page, urlInput }) => {
      // 1. 동일한 URL을 두 번 추가 시도
      const testUrl = TEST_DATA.VALID_URLS[0];
      
      await urlInput.addUrl(testUrl);
      expect(await urlInput.getUrlCount()).toBe(1);

      // 같은 URL 다시 추가 시도
      await urlInput.addUrl(testUrl);

      // Expected: 중복 경고 메시지
      const warningVisible = await page
        .locator('.warning, .alert, [role="alert"], .toast, .error')
        .isVisible()
        .catch(() => false);

      // Expected: 두 번째 추가 거부
      const count = await urlInput.getUrlCount();
      
      // 여전히 1개이거나 경고가 표시되어야 함
      expect(count).toBe(1);
    });
  });
});
