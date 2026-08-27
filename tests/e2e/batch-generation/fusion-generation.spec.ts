/**
 * 퓨전 분석 (Fusion) 테스트
 *
 * - 2개 URL 퓨전 → 퓨전 카드 (퓨전 뱃지) (API — ChatMock 필요)
 * - 퓨전 모드 CTA 전환 + URL 2개 이상 게이트 (UI)
 *   (구 '퓨전 옵션' 패널(웹 리서치/댓글 심층 분석 체크박스)은 새 UI에서 제거됨)
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('퓨전 분석 (Fusion)', () => {
  test.describe.configure({ timeout: 300_000 });

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('2개 URL 퓨전 → 퓨전 카드 (퓨전 뱃지)', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    test.skip(
      process.env.E2E_LIVE_GENERATION !== '1',
      '실제 ChatMock/YouTube 연동은 E2E_LIVE_GENERATION=1에서만 실행',
    );
    // 설정: 저비용 프리셋 (ChatMock Mini · 요약 · 짧게)
    await contentGenerator.applyCheapPreset();

    // URL 2개 추가
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);

    // "퓨전" 모드 선택
    await contentGenerator.selectMode('fusion');

    // "퓨전 분석 ×2" CTA 클릭
    const generateBtn = page
      .getByRole('button', { name: /퓨전 분석/ })
      .filter({ visible: true })
      .first();
    await expect(generateBtn).toBeEnabled();
    await generateBtn.click();

    // 결과 대기
    await contentGenerator.waitForResult(280_000);

    // 결과 카드 존재
    const resultCount = await contentGenerator.getResultCount();
    expect(resultCount).toBeGreaterThanOrEqual(1);

    // "퓨전" 뱃지 확인 (카드 내부 스코프)
    const fusionBadge = page
      .locator('[data-report-id]')
      .first()
      .getByText('퓨전', { exact: true });
    await expect(fusionBadge).toBeVisible();
  });

  test('퓨전 모드 CTA 전환 + URL 2개 이상 게이트', async ({
    page,
    urlInput,
    contentGenerator,
  }) => {
    // URL 0개 상태에서도 퓨전 모드 선택 가능 (모드 버튼 상시 표시)
    await contentGenerator.selectMode('fusion');

    // CTA가 '퓨전 분석'으로 교체되고 '콘텐츠 생성' CTA는 사라짐
    const fusionCta = page
      .getByRole('button', { name: /퓨전 분석/ })
      .filter({ visible: true })
      .first();
    await expect(fusionCta).toBeVisible();
    await expect(
      page.getByRole('button', { name: /콘텐츠 생성/ }).filter({ visible: true }),
    ).toHaveCount(0);

    // 퓨전은 URL 2개 이상 필요: 0개 → 비활성화
    await expect(fusionCta).toBeDisabled();

    // URL 1개 → 여전히 비활성화
    await urlInput.addUrl(TEST_DATA.VALID_URLS[0]);
    await expect(fusionCta).toBeDisabled();

    // URL 2개 → 활성화
    await urlInput.addUrl(TEST_DATA.VALID_URLS[1]);
    await expect(fusionCta).toBeEnabled();
  });
});
