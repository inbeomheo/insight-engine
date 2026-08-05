/**
 * 태블릿 뷰 반응형 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 *
 * 참고: 현재 UI는 xl(1280px) 미만에서 모바일 셸(MobileAppShell)을 렌더하므로
 * 태블릿(768px)에서는 모바일 셸 레이아웃이 표시되는 것이 정상 동작이다.
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('태블릿 뷰 @parallel @no-auth @responsive', () => {
  test.use({ viewport: { width: 768, height: 1024 } }); // iPad

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('태블릿에서 레이아웃이 적절히 조정됨', async ({ page }) => {
    // xl(1280px) 미만 → 데스크톱 레이아웃(사이드바)은 숨겨지고 모바일 셸이 표시됨
    await expect(page.locator('aside')).toBeHidden();

    // 모바일 셸의 URL 입력창 표시
    await expect(page.getByPlaceholder('URL 붙여넣기', { exact: true })).toBeVisible();

    // 브랜드 + 메인 헤딩 표시 (숨겨진 데스크톱 h1 중복 제외)
    await expect(page.getByText('Insight Engine')).toBeVisible();
    await expect(
      page.getByRole('heading', { level: 1, name: /어떤 자료를/ }).filter({ visible: true }).first()
    ).toBeVisible();
  });

  test('모든 기능 요소가 표시됨', async ({ page }) => {
    // URL 입력창
    await expect(page.getByPlaceholder('URL 붙여넣기', { exact: true })).toBeVisible();

    // 출력 스타일 4종 버튼 (요약/Q&A/퀴즈/리텐션 카드 — 숨겨진 데스크톱 중복 제외)
    const styleButtons = page
      .getByRole('button', { name: /스타일 선택/ })
      .filter({ visible: true });
    await expect(styleButtons).toHaveCount(4);

    // 생성 모드 버튼 (개별/통합/퓨전)
    for (const mode of ['개별', '통합', '퓨전']) {
      await expect(
        page.getByRole('button', { name: mode, exact: true }).filter({ visible: true }).first()
      ).toBeVisible();
    }

    // 생성 CTA + 하단 네비게이션
    await expect(
      page.getByRole('button', { name: /콘텐츠 생성/ }).filter({ visible: true }).first()
    ).toBeVisible();
    await expect(page.getByRole('navigation', { name: '모바일 하단 네비게이션' })).toBeVisible();
  });

  test('가로 스크롤 없음', async ({ page }) => {
    const hasHorizontalScroll = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });

    expect(hasHorizontalScroll).toBeFalsy();
  });
});
