/**
 * 메인 페이지 로드 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('메인 페이지 로드 @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('페이지 제목이 올바르게 표시됨', async ({ page }) => {
    await expect(page).toHaveTitle(/Insight Engine|콘텐츠 생성/i);
  });

  test('주요 UI 요소가 표시됨', async ({ page }) => {
    // 메인 헤딩 (학습 엔진 UI)
    await expect(page.getByRole('heading', { name: '어떤 자료를 콘텐츠로 만들까요?' })).toBeVisible();

    // URL 입력 필드
    await expect(page.locator('#url-input')).toBeVisible();

    // 생성 CTA 버튼 (숨겨진 모바일 셸 중복 제외)
    await expect(
      page.getByRole('button', { name: /콘텐츠 생성/ }).filter({ visible: true }).first()
    ).toBeVisible();
  });

  test('콘솔에 JavaScript 에러가 없음', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.reload();
    await page.waitForLoadState('networkidle');

    // 심각한 에러만 필터링 (무시해도 되는 에러 제외)
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('manifest')
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test('페이지가 5초 이내에 로드됨', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    const loadTime = Date.now() - startTime;

    // 개발 환경에서는 5초 이내 (프로덕션에서는 더 엄격하게 설정)
    expect(loadTime).toBeLessThan(5000);
  });
});
