import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

/**
 * Phase 5: UI/UX 품질 테스트
 * 반응형, 접근성, 필터/검색
 */

test.describe('반응형 레이아웃', () => {
  test('데스크톱(1280px) — 사이드바와 메인 영역이 나란히 표시된다', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 사이드바 visible
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // 메인 영역도 visible
    const main = page.locator('main');
    await expect(main).toBeVisible();
  });

  test('모바일(375px) — URL 입력과 메인 영역이 표시된다', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 메인 영역 visible
    await expect(page.locator('main')).toBeVisible();

    // URL 입력 visible
    await expect(page.locator('#url-input')).toBeVisible();
  });

  test('태블릿(768px) — 레이아웃이 깨지지 않는다', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 주요 요소 표시
    await expect(page.locator('#url-input')).toBeVisible();
    await expect(page.getByText('Insight Engine')).toBeVisible();

    // JavaScript 에러 없음
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.waitForTimeout(1000);
    expect(errors).toHaveLength(0);
  });
});

test.describe('접근성', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('주요 인터랙티브 요소에 aria-label이 있다', async ({ page }) => {
    // URL 입력
    const urlInput = page.locator('#url-input');
    await expect(urlInput).toHaveAttribute('aria-label');

    // 생성 설정 열기 버튼
    const settingsBtn = page.getByRole('button', { name: /생성 설정 열기/ });
    await expect(settingsBtn).toBeVisible();

    // 메뉴 버튼
    const menuBtn = page.getByRole('button', { name: /메뉴 열기/ });
    await expect(menuBtn).toBeVisible();
  });

  test('키보드로 URL 입력 → Enter → 칩 추가가 가능하다', async ({ page }) => {
    await page.locator('#url-input').focus();
    await page.keyboard.type(TEST_DATA.VALID_URLS[0]);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    // 칩 추가 확인
    await expect(page.getByText('dQw4w9WgXcQ')).toBeVisible();
  });

  test('JavaScript 콘솔 에러가 없다', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    expect(errors).toHaveLength(0);
  });
});

test.describe('필터 & 검색 (결과 카드 있을 때)', () => {
  test('결과가 없으면 FilterBar가 표시되지 않는다', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // 검색 입력이 보이지 않아야 함 (결과 없음)
    const searchInput = page.getByPlaceholder('결과 검색...');
    await expect(searchInput).not.toBeVisible();
  });

  test('localStorage에 결과가 있으면 FilterBar가 표시된다', async ({ page }) => {
    // localStorage에 가짜 결과 주입
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.evaluate(() => {
      const fakeReports = [
        {
          id: 'test-1',
          title: '테스트 블로그 포스트',
          content: '이것은 테스트 콘텐츠입니다.',
          html: '<p>이것은 테스트 콘텐츠입니다.</p>',
          style: 'blog_seo',
          style_label: 'Blog+SEO',
          url: 'https://youtube.com/watch?v=test1',
          time: '5',
          created_at: new Date().toISOString(),
          usage: { total_tokens: 100 },
        },
      ];
      localStorage.setItem('insight-engine-reports', JSON.stringify(fakeReports));
    });

    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    // FilterBar의 검색 입력이 보여야 함
    const searchInput = page.getByPlaceholder('결과 검색...');
    await expect(searchInput).toBeVisible();
  });
});
