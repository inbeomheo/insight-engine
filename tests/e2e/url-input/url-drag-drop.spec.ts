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
    await expect(page.getByText('dQw4w9WgXcQ')).toBeVisible();
  });

  test('드래그 중 오버레이가 표시되고, 나가면 사라진다', async ({ page }) => {
    // 드래그 진입
    await page.evaluate(() => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      dt.setData('text/plain', 'https://youtu.be/test123');
      target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
    });

    // 오버레이 텍스트 확인
    await expect(page.getByText('YouTube URL을 여기에 놓으세요')).toBeVisible();

    // 드래그 나감
    await page.evaluate(() => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      target.dispatchEvent(new DragEvent('dragleave', { dataTransfer: dt, bubbles: true }));
    });

    await page.waitForTimeout(300);
    await expect(page.getByText('YouTube URL을 여기에 놓으세요')).not.toBeVisible();
  });

  test('유효하지 않은 텍스트를 드롭하면 URL이 추가되지 않는다', async ({ page }) => {
    await page.evaluate(() => {
      const target = document.querySelector('main') || document.body;
      const dt = new DataTransfer();
      dt.setData('text/plain', 'https://google.com/not-youtube');

      target.dispatchEvent(new DragEvent('dragenter', { dataTransfer: dt, bubbles: true }));
      target.dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true }));
    });

    await page.waitForTimeout(500);

    // Badge 칩이 없어야 함
    const badges = page.locator('[class*="badge"], [class*="Badge"]');
    await expect(badges).toHaveCount(0);
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

    // videoId "jNQXAC9IVRw"가 1개만 있어야 함
    const chips = page.getByText('jNQXAC9IVRw');
    await expect(chips).toHaveCount(1);
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
    await expect(page.getByText('9bZkp7q19f0')).toBeVisible();
  });
});
