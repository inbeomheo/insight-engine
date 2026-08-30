/**
 * ROOT-002 회귀 테스트 — 대시보드/노트 페이지 스크롤 불가 버그
 *
 * 버그 (2026-08-30 사용자 제보):
 *   루트 레이아웃 <body className="overflow-hidden h-screen">이 전역 적용되어 있어
 *   문서 스크롤을 사용하는 /dashboard, /notes 페이지에서 마우스 휠 스크롤이 불가했다.
 *   (body overflow:hidden은 사용자 제스처 스크롤을 차단 — 프로그래밍 scrollTop만 통과)
 *
 * 수정 (layout.tsx, global-error.tsx):
 *   body에서 overflow-hidden h-screen 제거.
 *   홈(/)의 데스크톱 셸은 자체적으로 h-screen overflow-hidden을 갖고 있어 영향 없음.
 *
 * 실행:
 *   cd tests/e2e && npx playwright test doc-scroll-pages/ --workers=1
 */
import { test, expect } from '../fixtures/test-fixtures';

for (const route of ['/dashboard', '/notes']) {
  test(`${route} 페이지에서 휠 스크롤이 동작해야 함 @no-auth`, async ({ page }) => {
    await page.addInitScript(() => {
      // 문서 스크롤 여유를 만들 더미 리포트 (노트/대시보드 카드 콘텐츠)
      const reports = Array.from({ length: 12 }, (_, i) => ({
        id: `qa-dummy-${i}`,
        title: `회귀 테스트 더미 ${i + 1}`,
        content: '스크롤 회귀 테스트용 더미 콘텐츠입니다. '.repeat(80),
        html: `<p>${'스크롤 회귀 테스트용 더미 콘텐츠입니다. '.repeat(80)}</p>`,
        style: 'summary',
        createdAt: new Date(Date.now() - i * 3600e3).toISOString(),
        url: `https://example.com/${i}`,
      }));
      localStorage.setItem('insight-engine-reports', JSON.stringify(reports));
      localStorage.setItem('insight-engine-onboarding-done', 'true');
    });

    await page.goto(route);
    await page.waitForLoadState('networkidle');

    // 1. body에 overflow:hidden이 없어야 한다 (수정 전: "overflow-hidden h-screen")
    const bodyClass = await page.evaluate(() => document.body.className);
    expect(bodyClass).not.toContain('overflow-hidden');

    // 2. 문서 스크롤 여유가 있어야 한다 (페이지 콘텐츠가 뷰포트보다 김)
    await expect
      .poll(async () =>
        page.evaluate(() => document.documentElement.scrollHeight - document.documentElement.clientHeight)
      )
      .toBeGreaterThan(0);

    // 3. 실제 휠 스크롤이 동작해야 한다
    const before = await page.evaluate(() => window.scrollY);
    await page.mouse.move(683, 400);
    await page.mouse.wheel(0, 600);
    await page.waitForTimeout(400);
    const after = await page.evaluate(() => window.scrollY);
    expect(after).toBeGreaterThan(before);

    // 4. 휠 이벤트가 preventDefault되지 않아야 한다 (차단 레이어 없음)
    const prevented = await page.evaluate(() => {
      const ev = new WheelEvent('wheel', { deltaY: 240, cancelable: true, bubbles: true });
      document.body.dispatchEvent(ev);
      return ev.defaultPrevented;
    });
    expect(prevented).toBe(false);
  });
}

test('홈(/) 데스크톱 셸은 내부 ScrollArea로 스크롤 유지 @no-auth', async ({ page }) => {
  // body 잠금 해제 후에도 홈 레이아웃이 회귀하지 않았는지 검증
  await page.addInitScript(() => {
    const reports = Array.from({ length: 12 }, (_, i) => ({
      id: `qa-dummy-${i}`,
      title: `회귀 테스트 더미 ${i + 1}`,
      content: '스크롤 회귀 테스트용 더미 콘텐츠입니다. '.repeat(80),
      html: `<p>${'스크롤 회귀 테스트용 더미 콘텐츠입니다. '.repeat(80)}</p>`,
      style: 'summary',
      createdAt: new Date(Date.now() - i * 3600e3).toISOString(),
      url: `https://example.com/${i}`,
    }));
    localStorage.setItem('insight-engine-reports', JSON.stringify(reports));
    localStorage.setItem('insight-engine-onboarding-done', 'true');
  });

  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // 데스크톱 뷰포트에서 메인 콘텐츠 ScrollArea가 존재하고 스크롤 가능해야 한다
  const viewport = page.locator('#main-content [data-slot="scroll-area-viewport"]').first();
  await expect(viewport).toBeVisible();

  const maxScroll = await viewport.evaluate((el) => el.scrollHeight - el.clientHeight);
  expect(maxScroll).toBeGreaterThan(0);

  const before = await viewport.evaluate((el) => el.scrollTop);
  await page.mouse.move(800, 400);
  await page.mouse.wheel(0, 600);
  await page.waitForTimeout(400);
  const after = await viewport.evaluate((el) => el.scrollTop);
  expect(after).toBeGreaterThan(before);
});
