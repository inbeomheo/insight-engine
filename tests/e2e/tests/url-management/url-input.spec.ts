/**
 * URL 입력 및 관리 테스트 (통합)
 *
 * spec: specs/01-url-input-management.plan.md
 * seed: seed.spec.ts
 *
 * 학습엔진 UI 개편(2026-08) 기준으로 재작성:
 * - URL 검증 규칙: http(s) 스킴만 필수 (frontend/hooks/useUrls.ts)
 *   → YouTube 외 웹페이지/RSS/arXiv/Podcast URL도 전부 유효
 * - URL은 칩(Badge)으로 표시: 소스 타입 배지 + videoId(또는 호스트명) + "<라벨> 제거" 버튼
 * - 에러 메시지는 입력 바 하단에 3초간 표시 (InputWrapper)
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 */
import { test, expect, TEST_DATA } from '../../fixtures/test-fixtures';

test.describe('URL 입력 및 관리', () => {
  test.beforeEach(async ({ mainPage }) => {
    // 앱 접속 (온보딩 모달 자동 닫기) + URL 입력 필드 준비 대기
    await mainPage.goto();
    await mainPage.waitForReady();
  });

  test.describe('Suite 1: URL 입력', () => {
    test('TC-1.1: 유효한 YouTube URL 입력', async ({ page, urlInput }) => {
      // 1. URL 입력 필드에 YouTube URL 입력 후 Enter
      const testUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
      await urlInput.addUrl(testUrl);

      // Expected: URL 칩이 목록에 추가됨
      expect(await urlInput.getUrlChipCount()).toBe(1);

      // Expected: 입력 필드가 초기화됨
      await expect(page.locator('#url-input')).toHaveValue('');

      // Expected: 칩에 영상 정보(videoId) + 제거 버튼 표시
      await expect(page.getByText('dQw4w9WgXcQ', { exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'dQw4w9WgXcQ 제거' })).toBeVisible();
    });

    test('TC-1.2: youtu.be 단축 URL 입력', async ({ page, urlInput }) => {
      // 1. 단축 URL 입력 후 Enter
      await urlInput.addUrl('https://youtu.be/dQw4w9WgXcQ');

      // Expected: URL 칩이 정상 추가됨
      expect(await urlInput.getUrlChipCount()).toBe(1);

      // Expected: 단축 URL에서도 videoId가 추출되어 칩에 표시됨
      await expect(page.getByText('dQw4w9WgXcQ', { exact: true })).toBeVisible();
    });

    test('TC-1.3: 잘못된 URL 입력 시 에러 표시', async ({ page, urlInput }) => {
      const input = page.locator('#url-input');

      // 스킴 없는 URL / 비 http(s) 스킴 전부 거부되어야 함
      for (const invalidUrl of TEST_DATA.INVALID_URLS) {
        await urlInput.addUrl(invalidUrl);

        // Expected: "유효한 URL이 아닙니다" 에러 메시지 표시
        await expect(page.getByText(TEST_DATA.INVALID_URL_ERROR)).toBeVisible();

        // Expected: 입력값은 지워지지 않고 유지됨 (수정 기회 제공)
        await expect(input).toHaveValue(invalidUrl);

        // Expected: URL 칩이 추가되지 않음
        expect(await urlInput.getUrlChipCount()).toBe(0);
      }
    });

    test('TC-1.4: 빈 입력에서 Enter 시 아무 동작 없음', async ({ page, urlInput, contentGenerator }) => {
      // 1. URL 입력 필드가 비어있는 상태에서 Enter
      const input = page.locator('#url-input');
      await input.click();
      await input.press('Enter');
      await page.waitForTimeout(500);

      // Expected: 칩 추가 없음, 에러 메시지 없음
      expect(await urlInput.getUrlChipCount()).toBe(0);
      await expect(page.getByText(TEST_DATA.INVALID_URL_ERROR)).toBeHidden();

      // Expected: 생성도 시작되지 않음 (URL 0개이므로)
      expect(await contentGenerator.isLoading()).toBe(false);
    });

    test('TC-1.5: 일반 웹페이지 URL도 유효 (새 검증 규칙)', async ({ page, urlInput }) => {
      // 학습엔진 개편으로 http(s) URL이면 소스 타입 무관하게 허용됨
      await urlInput.addUrl('https://example.com/blog/post');

      // Expected: 에러 없이 칩 추가 (호스트명 라벨 + 제거 버튼)
      expect(await urlInput.getUrlChipCount()).toBe(1);
      await expect(page.getByText('example.com', { exact: true })).toBeVisible();
      await expect(page.getByRole('button', { name: 'example.com 제거' })).toBeVisible();
      await expect(page.getByText(TEST_DATA.INVALID_URL_ERROR)).toBeHidden();
    });
  });

  test.describe('Suite 2: URL 칩 관리', () => {
    test('TC-2.1: URL 삭제', async ({ page, urlInput }) => {
      // 1. URL 추가 후 칩의 제거 버튼 클릭
      await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
      expect(await urlInput.getUrlChipCount()).toBe(1);

      await urlInput.removeUrlByIndex(0);

      // Expected: 칩이 목록에서 제거되고 videoId 텍스트도 사라짐
      expect(await urlInput.getUrlChipCount()).toBe(0);
      await expect(page.getByText('jNQXAC9IVRw', { exact: true })).toBeHidden();
    });

    test('TC-2.2: 최대 10개 URL 제한', async ({ page, urlInput }) => {
      // 1. 10개 URL 추가
      for (let i = 0; i < 10; i++) {
        await urlInput.addUrl(`https://www.youtube.com/watch?v=test${i}`);
      }
      expect(await urlInput.getUrlChipCount()).toBe(10);

      // 2. 11번째 URL 추가 시도
      await urlInput.addUrl('https://www.youtube.com/watch?v=test10');

      // Expected: 최대 개수 경고 메시지 표시
      await expect(page.getByText('최대 10개까지 추가할 수 있습니다.')).toBeVisible();

      // Expected: 11번째 URL 추가 거부 (칩 10개 유지)
      expect(await urlInput.getUrlChipCount()).toBe(10);
      await expect(page.getByText('test10', { exact: true })).toBeHidden();
    });

    test('TC-2.3: 중복 URL 검증', async ({ page, urlInput }) => {
      // 1. 동일한 URL을 두 번 추가 시도
      const testUrl = TEST_DATA.VALID_URLS[0];

      await urlInput.addUrl(testUrl);
      expect(await urlInput.getUrlChipCount()).toBe(1);

      await urlInput.addUrl(testUrl);

      // Expected: 중복 경고 메시지 표시
      await expect(page.getByText('이미 추가된 URL입니다.')).toBeVisible();

      // Expected: 두 번째 추가 거부 (칩 1개 유지)
      expect(await urlInput.getUrlChipCount()).toBe(1);
    });
  });
});
