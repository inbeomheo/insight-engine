import { test, expect } from '../fixtures/test-fixtures';

test.describe('URL 드래그앤드롭 (전체 페이지)', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('YouTube URL 텍스트를 페이지에 드롭하면 URL이 추가된다', async ({ page }) => {
    const url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';

    // DataTransfer로 드롭 시뮬레이션
    await page.evaluate((dropUrl) => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      dt.setData('text/plain', dropUrl);

      target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
      target.dispatchEvent(new DragEvent('dragover', { dataTransfer: dt, bubbles: true }));
      target.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true }));
    }, url);

    await page.waitForTimeout(500);

    // URL 칩(Badge)이 추가되었는지 확인 — videoId "dQw4w9WgXcQ"
    // (모바일 셸의 전체 URL 텍스트와 strict 충돌 방지 위해 exact)
    await expect(page.getByText('dQw4w9WgXcQ', { exact: true })).toBeVisible();
    await expect(page.locator('[aria-label="dQw4w9WgXcQ 제거"]:visible')).toHaveCount(1);
  });

  test('드래그 중 오버레이가 표시되고, 나가면 사라진다', async ({ page }) => {
    // 드래그 진입
    await page.evaluate(() => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      dt.setData('text/plain', 'https://youtu.be/test123');
      target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
    });

    // 오버레이 텍스트 확인 (새 UI: YouTube 외 소스도 받으므로 문구 변경됨)
    await expect(page.getByText('URL을 여기에 놓으세요')).toBeVisible();

    // 드래그 나감
    await page.evaluate(() => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      target.dispatchEvent(new DragEvent('dragleave', { dataTransfer: dt, bubbles: true }));
    });

    await page.waitForTimeout(300);
    await expect(page.getByText('URL을 여기에 놓으세요')).not.toBeVisible();
  });

  test('유효한 URL이 없는 텍스트를 드롭하면 URL이 추가되지 않는다', async ({ page }) => {
    // 새 검증 규칙: http(s) URL은 전부 유효 → 스킴 없는 텍스트로 무효 드롭 검증
    await page.evaluate(() => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      dt.setData('text/plain', 'youtube.com/watch?v=abc 그냥 일반 텍스트');

      target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
      target.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true }));
    });

    await page.waitForTimeout(500);

    // URL 칩이 없어야 함 (제거 버튼 부재로 판정)
    await expect(page.locator('[aria-label$="제거"]:visible')).toHaveCount(0);
  });

  test('중복 URL 드롭 시 하나만 추가된다', async ({ page }) => {
    const url = 'https://www.youtube.com/watch?v=jNQXAC9IVRw';

    // 첫 번째 드롭
    await page.evaluate((dropUrl) => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      dt.setData('text/plain', dropUrl);
      target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
      target.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true }));
    }, url);
    await page.waitForTimeout(500);

    // 두 번째 드롭 (중복)
    await page.evaluate((dropUrl) => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      dt.setData('text/plain', dropUrl);
      target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
      target.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true }));
    }, url);
    await page.waitForTimeout(500);

    // videoId "jNQXAC9IVRw" 칩이 1개만 있어야 함 (숨겨진 모바일 셸 중복 제외)
    await expect(page.locator('[aria-label="jNQXAC9IVRw 제거"]:visible')).toHaveCount(1);
  });

  test('text/uri-list 형식 드롭도 처리된다', async ({ page }) => {
    const url = 'https://www.youtube.com/watch?v=9bZkp7q19f0';

    await page.evaluate((dropUrl) => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      dt.setData('text/uri-list', dropUrl);

      target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
      target.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true }));
    }, url);

    await page.waitForTimeout(500);
    await expect(page.getByText('9bZkp7q19f0', { exact: true })).toBeVisible();
  });
});
