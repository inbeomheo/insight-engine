import type { Page } from '@playwright/test';
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

/**
 * Phase 5: UI/UX 품질 테스트
 * 반응형, 접근성, 필터/검색
 *
 * 참고: 현재 UI는 xl(1280px) 미만에서 모바일 셸(MobileAppShell),
 * 1280px 이상에서 데스크톱 레이아웃(사이드바+메인)을 렌더한다.
 */

// 현재 뷰포트가 모바일 셸 구간(xl 미만)인지 판별
function isMobileShell(page: Page): boolean {
  return (page.viewportSize()?.width ?? 1280) < 1280;
}

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

  test('모바일(375px) — 모바일 셸과 URL 입력이 표시된다', async ({ page, mainPage }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await mainPage.goto();

    // xl(1280px) 미만 → 데스크톱 레이아웃(사이드바)은 숨김
    await expect(page.locator('aside')).toBeHidden();

    // 모바일 셸 URL 입력창 + 하단 네비게이션 표시
    await expect(page.getByPlaceholder('URL 붙여넣기', { exact: true })).toBeVisible();
    await expect(page.getByRole('navigation', { name: '모바일 하단 네비게이션' })).toBeVisible();
  });

  test('태블릿(768px) — 레이아웃이 깨지지 않는다', async ({ page, mainPage }) => {
    // JavaScript 에러 수집 (내비게이션 전에 리스너 등록)
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));

    await page.setViewportSize({ width: 768, height: 1024 });
    await mainPage.goto();

    // 주요 요소 표시 (xl 미만 → 모바일 셸 레이아웃)
    await expect(page.getByPlaceholder('URL 붙여넣기', { exact: true })).toBeVisible();
    await expect(page.getByText('Insight Engine')).toBeVisible();

    // 가로 스크롤 없음
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalScroll).toBeFalsy();

    // JavaScript 에러 없음
    expect(errors).toHaveLength(0);
  });
});

test.describe('접근성', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('주요 인터랙티브 요소에 aria-label이 있다', async ({ page }) => {
    if (isMobileShell(page)) {
      // 모바일 셸: URL 추가 버튼 / 입력 방식 그룹 / 하단 네비게이션
      await expect(
        page.getByRole('button', { name: 'URL 추가' }).filter({ visible: true }).first()
      ).toBeVisible();
      await expect(
        page.getByRole('group', { name: '입력 방식 선택' }).filter({ visible: true }).first()
      ).toBeVisible();
      await expect(page.getByRole('navigation', { name: '모바일 하단 네비게이션' })).toBeVisible();
    } else {
      // 데스크톱: URL 입력 aria-label
      await expect(page.locator('#url-input')).toHaveAttribute('aria-label', 'URL 입력');

      // 생성 설정 열기 버튼 (URL 입력 바)
      await expect(page.getByRole('button', { name: '생성 설정 열기', exact: true })).toBeVisible();

      // 헤더 설정 열기 버튼 ('생성 설정 열기'와의 부분 일치 회피 위해 exact)
      await expect(page.getByRole('button', { name: '설정 열기', exact: true })).toBeVisible();
    }
  });

  test('키보드로 URL 입력 → Enter → 칩 추가가 가능하다', async ({ page }) => {
    const url = TEST_DATA.VALID_URLS[1]; // dQw4w9WgXcQ
    const input = isMobileShell(page)
      ? page.getByPlaceholder('URL 붙여넣기', { exact: true })
      : page.locator('#url-input');
    await input.click();
    await page.keyboard.type(url);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    if (isMobileShell(page)) {
      // 모바일 칩: 전체 URL 텍스트 표시
      await expect(page.getByText(url)).toBeVisible();
    } else {
      // 데스크톱 칩: videoId 배지 (숨겨진 모바일 셸의 전체 URL 텍스트와 중복 회피 위해 exact)
      await expect(page.getByText('dQw4w9WgXcQ', { exact: true })).toBeVisible();
    }
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

  test('localStorage에 결과가 있으면 결과 목록이 표시된다', async ({ page, mainPage }) => {
    // 온보딩 완료 처리(시작하기 클릭 시 localStorage에 저장 → 재로드 후 재표시 안 됨)
    await mainPage.goto();

    // localStorage에 가짜 결과 주입
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

    if (isMobileShell(page)) {
      // 모바일 셸: FilterBar 대신 라이브러리 탭에서 결과 확인
      await page
        .getByRole('navigation', { name: '모바일 하단 네비게이션' })
        .getByRole('button', { name: '라이브러리' })
        .click();
      await expect(
        page
          .getByRole('heading', { name: '테스트 블로그 포스트' })
          .filter({ visible: true })
          .first()
      ).toBeVisible();
    } else {
      // 데스크톱: FilterBar의 검색 입력이 보여야 함
      const searchInput = page.getByPlaceholder('결과 검색...');
      await expect(searchInput).toBeVisible();
    }
  });
});
