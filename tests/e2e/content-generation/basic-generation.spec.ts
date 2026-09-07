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
    test.skip(
      process.env.E2E_LIVE_GENERATION !== '1',
      '실제 ChatMock/YouTube 연동은 E2E_LIVE_GENERATION=1에서만 실행',
    );
    await contentGenerator.applyCheapPreset();
    // 1. URL 추가
    await urlInput.addUrl(TEST_DATA.SHORT_VIDEO);
    await expect(page.locator('[aria-label$="제거"]')).toHaveCount(1);

    await contentGenerator.clickGenerate();

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

  test('URL 없이 생성 버튼을 실행할 수 없다', async ({ page }) => {
    const generateBtn = page.getByRole('button', { name: /콘텐츠 생성/ }).filter({ visible: true });
    await expect(generateBtn).toHaveCount(1);
    await expect(generateBtn).toBeDisabled();
  });

  test('생성 중 로딩 상태 표시', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    test.skip(
      process.env.E2E_LIVE_GENERATION !== '1',
      '실제 ChatMock/YouTube 연동은 E2E_LIVE_GENERATION=1에서만 실행',
    );
    await contentGenerator.applyCheapPreset();
    await urlInput.addUrl(TEST_DATA.SHORT_VIDEO);
    await contentGenerator.clickGenerate();
    await expect(page.getByLabel('콘텐츠 생성 중').first()).toBeVisible({ timeout: 5_000 });

    // 완료 대기 (다음 테스트 방해 방지)
    await contentGenerator.waitForResult(160_000);
  });
});
