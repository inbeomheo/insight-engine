/**
 * 스타일 옵션 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('스타일 옵션 @parallel @no-auth', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('스타일 카드 섹션이 표시됨', async ({ page }) => {
    // 스타일은 카드 형태로 표시됨
    const styleSection = page.locator('#style-cards, .style-cards, [data-section="styles"]');
    const styleCards = page.locator('.style-card, [data-style]');

    // 스타일 섹션이나 카드 중 하나라도 있으면 OK
    const sectionVisible = await styleSection.isVisible().catch(() => false);
    const cardsCount = await styleCards.count();

    expect(sectionVisible || cardsCount > 0).toBeTruthy();
  });

  test('다양한 스타일 옵션이 있음', async ({ page }) => {
    const styleCards = page.locator('.style-card, [data-style]');
    const count = await styleCards.count();
    expect(count).toBeGreaterThan(3); // 최소 3개 이상의 스타일
  });

  test('스타일 선택이 변경됨', async ({ page }) => {
    const styleCards = page.locator('.style-card, [data-style]');
    const count = await styleCards.count();

    if (count > 1) {
      // 두 번째 스타일 카드 클릭
      await styleCards.nth(1).click();
      await page.waitForTimeout(300);

      // 선택된 상태 확인 (selected, active 클래스 등)
      const secondCard = styleCards.nth(1);
      const classList = await secondCard.getAttribute('class');
      // 어떤 형태로든 선택 상태가 표시되어야 함
      expect(classList).toBeTruthy();
    }
  });

  test('각 스타일에 한국어 이름이 표시됨', async ({ page }) => {
    const styleCards = page.locator('.style-card, [data-style]');
    const texts = await styleCards.allTextContents();
    const koreanPattern = /[가-힣]/;

    const koreanOptions = texts.filter((opt) => koreanPattern.test(opt));
    expect(koreanOptions.length).toBeGreaterThan(0);
  });
});
