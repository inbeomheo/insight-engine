import type { Page } from '@playwright/test';
import { test, expect, TEST_DATA, injectReports, makeMockReport } from '../fixtures/test-fixtures';

const URLS = TEST_DATA.VALID_URLS.slice(0, 3);
const FIRST_SUCCESS = URLS[0];
const RETRY_URLS = URLS.slice(1);
const FAILURE_MESSAGE = '자막을 불러올 수 없습니다.';
const RESULTS = URLS.map((url, index) => makeMockReport({
  url,
  title: `일괄 생성 결과 ${index + 1}`,
  content: `자료 ${index + 1}의 학습 내용을 정리했습니다.`,
  html: `<p>자료 ${index + 1}의 학습 내용을 정리했습니다.</p>`,
}));

function queuedUrl(page: Page, url: string, mobile: boolean) {
  if (mobile) {
    return page.getByRole('button', { name: 'URL 제거', exact: true })
      .filter({ visible: true }).locator('..').filter({ hasText: url });
  }
  const videoId = new URL(url).searchParams.get('v');
  return page.getByRole('button', { name: `${videoId} 제거`, exact: true })
    .filter({ visible: true });
}

async function storedReports(page: Page) {
  return page.evaluate(() => {
    const reports: { url: string; title: string; content: string }[] = JSON.parse(
      localStorage.getItem('insight-engine-reports') || '[]',
    );
    return reports.map(({ url, title, content }) => ({ url, title, content }))
      .sort((a, b) => a.url.localeCompare(b.url));
  });
}

function expectedReports(urls: readonly string[]) {
  return RESULTS.filter((report) => urls.includes(report.url))
    .map(({ url, title, content }) => ({ url, title, content }))
    .sort((a, b) => a.url.localeCompare(b.url));
}

for (const viewport of [
  { label: '데스크톱', width: 1280, height: 900, mobile: false },
  { label: '모바일 375px', width: 375, height: 812, mobile: true },
]) {
  test(`${viewport.label}: 부분 성공 후 실패 URL만 재시도하고 결과를 저장한다`, async ({ page, mainPage, contentGenerator }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await injectReports(page, []);
    await page.addInitScript(() => {
      localStorage.setItem('insight-engine-selected-model', JSON.stringify('cliproxyapi/gpt-5.5'));
    });

    const submittedBatches: string[][] = [];
    // 실패 URL 두 개를 남겨 재시도도 /generate-batch만 사용한다.
    // 생성 요청은 브라우저에서 응답하므로 외부 AI나 서버 데이터에 접근하지 않는다.
    await page.route('**/generate-batch', async (route) => {
      expect(route.request().method()).toBe('POST');
      const { urls } = route.request().postDataJSON() as { urls: string[] };
      submittedBatches.push(urls);
      expect(submittedBatches.length).toBeLessThanOrEqual(2);
      expect(urls).toEqual(submittedBatches.length === 1 ? URLS : RETRY_URLS);

      const results = urls.map((url) => {
        if (submittedBatches.length === 1 && url !== FIRST_SUCCESS) {
          return { url, success: false, error: FAILURE_MESSAGE };
        }
        return { ...RESULTS.find((report) => report.url === url), success: true };
      });
      // 응답 순서가 바뀌어도 URL별 성공 여부를 적용해야 한다.
      await route.fulfill({ json: { results: results.reverse() } });
    });

    await mainPage.goto();
    const input = viewport.mobile
      ? page.getByRole('textbox', { name: '분석할 URL 입력', exact: true })
      : page.locator('#url-input');
    for (const url of URLS) {
      await input.fill(url);
      await input.press('Enter');
      await expect(queuedUrl(page, url, viewport.mobile)).toBeVisible();
    }

    await contentGenerator.clickGenerateByMode('individual');
    const warning = page.locator('[data-sonner-toast]').filter({ hasText: '2개 URL 처리 실패' });
    await expect(warning).toBeVisible();
    await expect(warning).toContainText(FAILURE_MESSAGE);
    for (const url of RETRY_URLS) {
      await expect(warning).toContainText(url);
      await expect(queuedUrl(page, url, viewport.mobile)).toBeVisible();
    }
    await expect(queuedUrl(page, FIRST_SUCCESS, viewport.mobile)).toHaveCount(0);
    await expect.poll(() => storedReports(page)).toEqual(expectedReports([FIRST_SUCCESS]));

    const mobileNav = page.getByRole('navigation', { name: '모바일 하단 네비게이션' });
    if (viewport.mobile) {
      await mobileNav.getByRole('button', { name: '라이브러리', exact: true }).click();
      await expect(page.getByRole('heading', { name: RESULTS[0].title, exact: true })
        .filter({ visible: true })).toBeVisible();
      await mobileNav.getByRole('button', { name: '생성', exact: true }).click();
    } else {
      const cards = page.locator('[data-report-id]').filter({ visible: true });
      await expect(cards).toHaveCount(1);
      await expect(cards).toContainText(RESULTS[0].title);
    }

    const retryButton = page.getByRole('button', { name: /콘텐츠 생성 ×2/ })
      .filter({ visible: true }).first();
    await expect(retryButton).toBeEnabled();
    await retryButton.click();

    await expect.poll(() => submittedBatches).toEqual([URLS, RETRY_URLS]);
    for (const url of URLS) {
      await expect(queuedUrl(page, url, viewport.mobile)).toHaveCount(0);
    }
    await expect.poll(() => storedReports(page)).toEqual(expectedReports(URLS));
    await expect(page.getByRole('button', { name: /콘텐츠 생성/ })
      .filter({ visible: true }).first()).toBeDisabled();

    if (viewport.mobile) {
      await mobileNav.getByRole('button', { name: '라이브러리', exact: true }).click();
      for (const result of RESULTS) {
        await expect(page.getByRole('heading', { name: result.title, exact: true })
          .filter({ visible: true })).toBeVisible();
      }
    } else {
      const cards = page.locator('[data-report-id]').filter({ visible: true });
      await expect(cards).toHaveCount(3);
      for (const result of RESULTS) {
        await expect(cards.filter({ hasText: result.title })).toHaveCount(1);
      }
    }
  });
}
