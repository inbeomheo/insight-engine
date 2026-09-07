/**
 * 모바일 뷰 반응형 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import type { Page } from '@playwright/test';
import {
  expect,
  injectReports,
  makeMockReport,
  test,
} from '../fixtures/test-fixtures';

async function expectNoHorizontalOverflow(page: Page) {
  const metrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth);
}

test.describe('모바일 뷰 @parallel @no-auth @responsive', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  // 회귀 방지(#47): body가 `overflow-hidden h-screen`으로 잠겨 있으면
  // 첫 화면 아래 콘텐츠(스타일 선택 · 생성 모드 · 생성 버튼)에 아예 도달할 수 없다.
  test('짧은 화면에서도 첫 화면 아래 콘텐츠까지 세로 스크롤로 도달한다', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    const scrollable = await page.evaluate(() => {
      const d = document.documentElement;
      return d.scrollHeight > d.clientHeight;
    });
    expect(scrollable).toBeTruthy();

    const generateButton = page.getByRole('button', { name: /콘텐츠 생성/ });
    await expect(generateButton).toBeVisible();
    await generateButton.scrollIntoViewIfNeeded();

    await generateButton.evaluate((element) => {
      element.scrollIntoView({ block: 'center' });
    });

    const box = await generateButton.boundingBox();
    const navBox = await page
      .getByRole('navigation', { name: '모바일 하단 네비게이션' })
      .boundingBox();
    expect(box).not.toBeNull();
    expect(navBox).not.toBeNull();
    // 생성 CTA가 하단 고정 nav 밑에 가려지지 않아야 한다.
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(navBox!.y);
  });

  test('모바일에서 레이아웃이 깨지지 않음', async ({ page }) => {
    // 가로 스크롤 확인
    await expectNoHorizontalOverflow(page);
  });

  test('보이는 모바일 버튼은 44px 터치 높이를 확보한다', async ({ page }) => {
    const buttons = page.locator('button:visible');
    const count = await buttons.count();

    expect(count).toBeGreaterThan(5);
    for (let i = 0; i < count; i++) {
      const el = buttons.nth(i);
      const box = await el.boundingBox();

      if (box) {
        const label = await el.getAttribute('aria-label') || await el.textContent() || `button ${i}`;
        // Next 개발 서버가 삽입하는 디버그 오버레이는 제품 UI가 아니다.
        if (label.includes('Next.js Dev Tools')) continue;
        expect(box.height, label.trim()).toBeGreaterThanOrEqual(44);
      }
    }
  });

  test('텍스트가 읽기 쉬운 크기', async ({ page }) => {
    const textElements = page.locator('p, span, div, label, h1, h2, h3');
    const firstText = textElements.first();

    if (await firstText.isVisible()) {
      const fontSize = await firstText.evaluate((el) => {
        return parseFloat(getComputedStyle(el).fontSize);
      });

      // 최소 12px 이상
      expect(fontSize).toBeGreaterThanOrEqual(12);
    }
  });

  test('입력 필드가 화면 너비에 맞음', async ({ page }) => {
    const input = page.locator('input:visible').first();

    if (await input.isVisible()) {
      const box = await input.boundingBox();
      const viewportWidth = 375;

      if (box) {
        expect(box.x).toBeGreaterThanOrEqual(0);
        expect(box.x + box.width).toBeLessThanOrEqual(viewportWidth);
      }
    }
  });

  for (const width of [360, 375, 390, 430]) {
    test(`${width}px 폭에서 생성 화면이 가로로 잘리지 않는다`, async ({ page, mainPage }) => {
      await page.setViewportSize({ width, height: 812 });
      await mainPage.goto();
      await expectNoHorizontalOverflow(page);
      await expect(page.getByRole('button', { name: /콘텐츠 생성/ })).toBeVisible();
      await expect(
        page.getByRole('navigation', { name: '모바일 하단 네비게이션' }),
      ).toBeVisible();
    });
  }

  test('375x812 생성·라이브러리·대시보드·상세·영상 질문 전체 스모크', async ({ page }) => {
    const consoleErrors: string[] = [];
    const pageErrors: string[] = [];
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text());
    });
    page.on('pageerror', (error) => pageErrors.push(error.message));

    await page.route('**/api/video-qa', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          answer: '모바일 질문 응답',
          sources: [{ text: '검증용 자막 근거', relevance: 0.91 }],
        }),
      });
    });
    await injectReports(page, [makeMockReport({
      id: 'mobile-smoke-report',
      title: '모바일 전체 흐름 리포트',
      content: '공백없는긴문자열'.repeat(30),
      html: `<p>${'공백없는긴문자열'.repeat(30)}</p>`,
    })]);
    await page.reload();
    await page.waitForLoadState('networkidle');

    await expect(page.getByPlaceholder('URL 붙여넣기', { exact: true })).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await expect(page.locator('meta[name="viewport"]')).toHaveAttribute(
      'content',
      /viewport-fit=cover/,
    );

    const nav = page.getByRole('navigation', { name: '모바일 하단 네비게이션' });
    await nav.getByRole('button', { name: '라이브러리' }).click();
    await expect(page.getByRole('heading', { name: '라이브러리' })).toBeVisible();
    await expect(page.getByRole('heading', { name: '모바일 전체 흐름 리포트' })).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await nav.getByRole('button', { name: '대시보드' }).click();
    await expect(page.getByRole('heading', { name: '대시보드' })).toBeVisible();
    await expect(page.getByText('총 콘텐츠')).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await nav.getByRole('button', { name: '라이브러리' }).click();
    await page.getByRole('heading', { name: '모바일 전체 흐름 리포트' }).click();
    await expect(page.getByRole('button', { name: '뒤로가기' })).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.getByRole('button', { name: '영상에 질문하기' }).first().click();
    const questionInput = page.getByPlaceholder(/질문을 입력하세요/);
    await expect(questionInput).toBeVisible();
    await expectNoHorizontalOverflow(page);
    await questionInput.fill('핵심 내용은 무엇인가요?');
    await page.getByRole('button', { name: '질문 전송' }).click();

    const sourceToggle = page.getByRole('button', { name: '자막 근거 펼치기' });
    await expect(sourceToggle).toBeVisible();
    const sourceToggleBox = await sourceToggle.boundingBox();
    expect(sourceToggleBox).not.toBeNull();
    expect(sourceToggleBox!.height).toBeGreaterThanOrEqual(44);
    await sourceToggle.click();
    await expect(page.getByText('검증용 자막 근거')).toBeVisible();
    await page.getByRole('button', { name: '영상 채팅 패널 닫기' }).click();

    await page.waitForTimeout(100);
    expect(pageErrors).toEqual([]);
    expect(consoleErrors).toEqual([]);
  });
});
