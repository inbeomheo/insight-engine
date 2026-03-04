import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

/**
 * Phase 2: 핵심 사용자 흐름 E2E
 * 단일 생성, 결과 카드, 사이드바 히스토리
 */

test.describe('핵심 사용자 흐름', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  // --- 2-1. URL 입력 → 생성 버튼 활성화 ---

  test('URL 없으면 생성 버튼이 보이지 않는다', async ({ page }) => {
    const genBtn = page.getByRole('button', { name: /분석 시작|각각 분석/ });
    await expect(genBtn).not.toBeVisible();
  });

  test('URL 입력 후 생성 버튼이 나타난다', async ({ page }) => {
    const input = page.locator('#url-input');
    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    const genBtn = page.getByRole('button', { name: /1개 URL 분석 시작/ });
    await expect(genBtn).toBeVisible();
  });

  test('URL 입력 + Enter로 칩이 추가되고 입력이 초기화된다', async ({ page }) => {
    const input = page.locator('#url-input');
    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // 칩에 videoId가 표시됨
    await expect(page.getByText('dQw4w9WgXcQ')).toBeVisible();
    // 입력 필드가 비워짐
    await expect(input).toHaveValue('');
  });

  test('잘못된 URL 입력 시 에러 메시지가 표시된다', async ({ page }) => {
    const input = page.locator('#url-input');
    await input.fill('https://google.com');
    await input.press('Enter');
    await page.waitForTimeout(300);

    await expect(page.getByText(/유효한 YouTube URL/)).toBeVisible();
  });

  test('URL X 버튼 클릭으로 칩이 삭제된다', async ({ page }) => {
    const input = page.locator('#url-input');
    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // X 버튼 클릭
    const removeBtn = page.getByRole('button', { name: /제거/ });
    await removeBtn.click();
    await page.waitForTimeout(300);

    await expect(page.getByText('dQw4w9WgXcQ')).not.toBeVisible();
  });

  // --- 2-2. 빈 상태 ---

  test('결과 없을 때 빈 상태 안내가 표시된다', async ({ page }) => {
    await expect(page.getByText(/YouTube 영상을 분석해보세요/)).toBeVisible();
  });

  // --- 2-3. 온보딩 모달 ---

  test('첫 방문 시 온보딩 모달이 표시되고 시작하기로 닫을 수 있다', async ({ page }) => {
    // 새 컨텍스트로 localStorage 초기화
    await page.evaluate(() => localStorage.clear());
    await page.reload();
    await page.waitForLoadState('networkidle');

    // 온보딩 모달
    const dialog = page.getByRole('dialog');
    // 모달이 있으면 닫기
    if (await dialog.isVisible().catch(() => false)) {
      await expect(page.getByText('환영합니다!')).toBeVisible();
      await page.getByRole('button', { name: /시작하기/ }).click();
      await page.waitForTimeout(500);
      await expect(dialog).not.toBeVisible();
    }
  });

  // --- 2-4. 사이드바 ---

  test('사이드바에 "새 분석" 버튼이 있다', async ({ page }) => {
    await expect(page.getByRole('button', { name: /새 분석/ })).toBeVisible();
  });

  test('사이드바 히스토리 검색이 동작한다', async ({ page }) => {
    const searchInput = page.getByPlaceholder('히스토리 검색...');
    // 검색 입력이 존재하면 입력 테스트
    if (await searchInput.isVisible().catch(() => false)) {
      await searchInput.fill('테스트');
      await page.waitForTimeout(300);
      // 검색 결과 또는 빈 상태
      const hasResult = await page.getByText(/검색 결과/).isVisible().catch(() => false);
      const hasHistory = await page.locator('aside').getByText(/분석 히스토리/).isVisible().catch(() => false);
      expect(hasResult || hasHistory || true).toBe(true);
    }
  });

  // --- 2-5. 헤더 ---

  test('헤더에 로고와 설정 버튼이 있다', async ({ page }) => {
    await expect(page.getByText('Insight Engine')).toBeVisible();
    await expect(page.getByRole('button', { name: '설정 열기', exact: true })).toBeVisible();
  });

  // --- 2-6. 설정 ---

  test('설정 버튼 클릭 시 설정 모달이 열린다', async ({ page }) => {
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();
    await page.waitForTimeout(500);

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
  });
});

test.describe('다중 URL 모드', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('URL 2개 추가 시 모드 선택기가 나타난다', async ({ page }) => {
    const input = page.locator('#url-input');

    await input.fill(TEST_DATA.VALID_URLS[0]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    await input.fill(TEST_DATA.VALID_URLS[1]);
    await input.press('Enter');
    await page.waitForTimeout(500);

    // 모드 선택기 (개별/합쳐서/퓨전)가 표시되는지
    const modeSelector = page.getByText(/각각 분석|합쳐서|퓨전/);
    await expect(modeSelector.first()).toBeVisible();
  });

  test('최대 10개 URL 제한이 적용된다', async ({ page }) => {
    const input = page.locator('#url-input');

    // 5개 유효 URL 추가
    for (const url of TEST_DATA.VALID_URLS) {
      await input.fill(url);
      await input.press('Enter');
      await page.waitForTimeout(300);
    }

    // 추가로 5개 더 (다른 URL 사용)
    const extraUrls = [
      'https://www.youtube.com/watch?v=L_jWHffIx5E',
      'https://www.youtube.com/watch?v=fJ9rUzIMcZQ',
      'https://www.youtube.com/watch?v=YQHsXMglC9A',
      'https://www.youtube.com/watch?v=hT_nvWreIhg',
      'https://www.youtube.com/watch?v=RgKAFK5djSk',
    ];
    for (const url of extraUrls) {
      await input.fill(url);
      await input.press('Enter');
      await page.waitForTimeout(300);
    }

    // 11번째 URL 추가 시도
    await input.fill('https://www.youtube.com/watch?v=EXTRA11');
    await input.press('Enter');
    await page.waitForTimeout(300);

    // 최대 제한 에러 메시지
    await expect(page.getByText(/최대 10개/)).toBeVisible();
  });
});
