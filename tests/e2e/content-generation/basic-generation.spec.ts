/**
 * 기본 콘텐츠 생성 테스트
 *
 * - 단일 URL 생성 → 결과 카드 표시 (API)
 * - URL 없이 생성 버튼 미표시 (UI)
 * - 생성 중 로딩 상태 표시 (API)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('기본 콘텐츠 생성', () => {
  // API 테스트는 시간이 오래 걸림 — 기본 타임아웃 3배
  test.describe.configure({ timeout: 180_000 });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('단일 URL 생성 → 결과 카드 표시', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    // 1. URL 추가
    await urlInput.addUrl(TEST_DATA.SHORT_VIDEO);
    await expect(page.locator('[aria-label$="제거"]')).toHaveCount(1);

    // 2. "1개 URL 분석 시작" 버튼 클릭
    const generateBtn = page.getByRole('button', { name: /1개 URL 분석 시작/ });
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    // 3. 결과 카드 대기
    await contentGenerator.waitForResult(160_000);

    // 4. 결과 카드 검증
    const card = page.locator('[data-report-id]').first();
    await expect(card).toBeVisible();

    // 제목이 존재 (카드 헤더 영역의 첫 h3)
    const title = card.locator('h3').first();
    await expect(title).not.toBeEmpty();

    // 본문이 존재 (prose 영역)
    const body = card.locator('.prose');
    await expect(body).toBeVisible();
  });

  test('URL 없이 생성 버튼이 표시되지 않음', async ({ page }) => {
    // URL이 없을 때 분석 버튼이 없어야 함
    const generateBtn = page.getByRole('button', {
      name: /분석 시작|각각 분석|합쳐서 분석|퓨전 분석/,
    });
    await expect(generateBtn).toHaveCount(0);
  });

  test('생성 중 로딩 상태 표시', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    await urlInput.addUrl(TEST_DATA.SHORT_VIDEO);

    const generateBtn = page.getByRole('button', { name: /1개 URL 분석 시작/ });
    await generateBtn.click();

    // 버튼 텍스트가 "생성 중..."으로 변경됨
    const loadingBtn = page.getByRole('button', { name: /생성 중/ });
    await expect(loadingBtn).toBeVisible({ timeout: 5_000 });

    // 로딩 스켈레톤도 표시됨
    const skeleton = page.locator('[class*="animate-pulse"], [class*="skeleton"]');
    const skeletonVisible = await skeleton.first().isVisible().catch(() => false);
    // 스켈레톤은 선택적 — 최소한 로딩 버튼은 확인
    expect(skeletonVisible || await loadingBtn.isVisible()).toBeTruthy();

    // 완료 대기 (다음 테스트 방해 방지)
    await contentGenerator.waitForResult(160_000);
  });
});
