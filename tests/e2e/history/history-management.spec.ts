import { test, expect, injectReports, makeMockReport } from '../fixtures/test-fixtures';

test.describe('브라우저 히스토리 @parallel @no-auth', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('빈 저장소는 빈 안내를 표시한다', async ({ page, mainPage }) => {
    await injectReports(page, []);
    await mainPage.goto();
    const sidebar = page.getByRole('navigation', { name: '사이드바 내비게이션' });
    await expect(sidebar).toBeVisible();
    await expect(sidebar.getByText('분석 히스토리가 없습니다', { exact: true })).toBeVisible();
    await expect(sidebar.getByRole('button', { name: /히스토리 보기$/ })).toHaveCount(0);
    await expect(sidebar.getByRole('button', { name: /^전체 삭제/ })).toHaveCount(0);
  });

  test('저장된 결과를 검색하고 선택하면 해당 결과가 활성화된다', async ({ page, mainPage }) => {
    await injectReports(page, [
      makeMockReport({ id: 'history-alpha', title: '분산 시스템 입문', youtube_title: '분산 강의' }),
      makeMockReport({ id: 'history-beta', title: '데이터 구조 복습', youtube_title: '자료구조 강의' }),
    ]);
    await mainPage.goto();
    const sidebar = page.getByRole('navigation', { name: '사이드바 내비게이션' });
    const entries = sidebar.getByRole('button', { name: /히스토리 보기$/ });
    await expect(entries).toHaveCount(2);
    const search = sidebar.getByPlaceholder('히스토리 검색...');
    await search.fill('자료구조');
    await expect(entries).toHaveCount(1);
    await expect(entries).toHaveAttribute('aria-label', '데이터 구조 복습 히스토리 보기');
    await entries.click();
    await expect(entries).toHaveAttribute('aria-current', 'true');
    await expect(page.locator('[data-report-id="history-beta"]')).toBeVisible();
    await search.fill('존재하지 않는 검색어');
    await expect(sidebar.getByText('검색 결과가 없습니다', { exact: true })).toBeVisible();
    await expect(entries).toHaveCount(0);
    await search.clear();
    await expect(entries).toHaveCount(2);
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('insight-engine-reports') ?? '[]').length)).toBe(2);
  });

  test('다른 계정의 저장 결과는 익명 히스토리에 섞이지 않는다', async ({ page, mainPage }) => {
    await injectReports(page, [makeMockReport({ id: 'anonymous-report', title: '익명 브라우저 결과' })]);
    await page.addInitScript(report => {
      localStorage.setItem('insight-engine-reports:account:user:another-account', JSON.stringify([report]));
    }, makeMockReport({ id: 'private-report', title: '다른 계정의 비공개 결과' }));
    await mainPage.goto();
    const sidebar = page.getByRole('navigation', { name: '사이드바 내비게이션' });
    await expect(sidebar.getByRole('button', { name: '익명 브라우저 결과 히스토리 보기' })).toBeVisible();
    await expect(sidebar.getByRole('button', { name: '다른 계정의 비공개 결과 히스토리 보기' })).toHaveCount(0);
    await expect(page.locator('[data-report-id="private-report"]')).toHaveCount(0);
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('insight-engine-reports:account:user:another-account') ?? '[]')[0].id))
      .toBe('private-report');
  });
});
