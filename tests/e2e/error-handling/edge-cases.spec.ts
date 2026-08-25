import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

/**
 * Phase 4: 에러 & 엣지케이스 E2E
 */

test.describe('입력 엣지케이스', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('빈 입력 제출 시 URL이 추가되지 않는다', async ({ page }) => {
    const input = page.locator('#url-input');
    await input.press('Enter');
    await page.waitForTimeout(300);

    // Badge 칩이 없어야 함
    const badges = page.locator('[class*="badge"], [class*="Badge"]').filter({ hasText: /\w{5,}/ });
    await expect(badges).toHaveCount(0);
  });

  test('특수 문자가 포함된 URL 처리', async ({ page, urlInput }) => {
    const input = page.locator('#url-input');
    await input.fill('<script>alert(1)</script>');
    await input.press('Enter');
    await page.waitForTimeout(300);

    // http(s) 스킴이 없으므로 거부되고 에러 메시지가 표시됨
    await expect(page.getByText(TEST_DATA.INVALID_URL_ERROR)).toBeVisible();
    expect(await urlInput.getUrlChipCount()).toBe(0);
  });

  test('중복 URL 입력 시 에러 메시지가 표시된다', async ({ page }) => {
    const input = page.locator('#url-input');
    const url = TEST_DATA.VALID_URLS[0];

    // 첫 번째 추가
    await input.fill(url);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // 같은 URL 다시 추가
    await input.fill(url);
    await input.press('Enter');
    await page.waitForTimeout(300);

    await expect(page.getByText(/이미 추가된/)).toBeVisible();
  });

  test('Vimeo 등 일반 웹페이지 URL은 Web 소스로 추가된다', async ({ page, urlInput }) => {
    const input = page.locator('#url-input');
    await input.fill('https://vimeo.com/123456789');
    await input.press('Enter');
    await page.waitForTimeout(300);

    // 새 검증 규칙: http(s) URL은 전부 허용 — 에러 없이 Web 배지 칩으로 추가됨
    await expect(page.getByText(TEST_DATA.INVALID_URL_ERROR)).not.toBeVisible();
    expect(await urlInput.getUrlChipCount()).toBe(1);
    await expect(page.getByText('vimeo.com', { exact: true })).toBeVisible();
    await expect(page.getByText('Web', { exact: true })).toBeVisible();
  });
});

test.describe('동시성', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('빠른 연속 URL 추가가 정상 처리된다', async ({ page, urlInput }) => {
    const input = page.locator('#url-input');

    // 3개 URL을 빠르게 연속 추가
    for (const url of TEST_DATA.VALID_URLS.slice(0, 3)) {
      await input.fill(url);
      await input.press('Enter');
      await page.waitForTimeout(200);
    }

    await page.waitForTimeout(500);

    // 3개 칩이 보여야 함 (모바일 셸의 전체 URL 텍스트와 충돌 방지를 위해 exact 매칭)
    expect(await urlInput.getUrlChipCount()).toBe(3);
    await expect(page.getByText('jNQXAC9IVRw', { exact: true })).toBeVisible();
    await expect(page.getByText('dQw4w9WgXcQ', { exact: true })).toBeVisible();
    await expect(page.getByText('9bZkp7q19f0', { exact: true })).toBeVisible();
  });

  test('페이지 새로고침 후 크래시 없이 로드된다', async ({ page }) => {
    // URL 추가
    const input = page.locator('#url-input');
    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // 새로고침
    await page.reload();
    await page.waitForLoadState('networkidle');

    // 페이지가 정상 로드됨 (URL은 state이므로 초기화됨)
    await expect(page.locator('#url-input')).toBeVisible();
    await expect(
      page.getByRole('heading', { name: '어떤 자료를 콘텐츠로 만들까요?' })
    ).toBeVisible();
  });
});

test.describe('API 에러 응답', () => {
  test('존재하지 않는 API 엔드포인트 요청 시 에러', async ({ page }) => {
    const response = await page.request.get('/api/nonexistent');
    expect(response.status()).toBeGreaterThanOrEqual(400);
  });

  test('/generate에 빈 body POST 시 에러 응답', async ({ page }) => {
    const response = await page.request.post('/generate', {
      data: {},
      headers: { 'Content-Type': 'application/json' },
    });
    const body = await response.json();
    expect(body.error).toBeDefined();
  });

  test('/generate에 잘못된 URL POST 시 에러 응답', async ({ page }) => {
    const response = await page.request.post('/generate', {
      data: { url: 'not-a-youtube-url', style: 'summary' },
      headers: { 'Content-Type': 'application/json' },
    });
    const body = await response.json();
    expect(body.error).toBeDefined();
  });
});
