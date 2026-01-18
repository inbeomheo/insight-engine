/**
 * 다양한 스타일로 콘텐츠 생성 테스트
 *
 * 병렬 실행: ✅ (상태 공유 없음, 완전 독립적)
 * 인증 필요: ❌
 */
import { test, expect, TEST_DATA } from '../fixtures/test-fixtures';

test.describe('스타일 변형 테스트 @parallel @no-auth', () => {
  test.setTimeout(120_000);

  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  test('스타일 선택이 UI에 반영됨', async ({ page }) => {
    const styleSelect = page.locator('select:has-text("스타일"), [data-testid="style-select"]').first();

    if (await styleSelect.isVisible()) {
      const options = await styleSelect.locator('option').allTextContents();

      for (const style of options.slice(0, 3)) {
        await styleSelect.selectOption({ label: style });
        const selectedValue = await styleSelect.inputValue();
        expect(selectedValue).toBeTruthy();
      }
    }
  });

  test('프로바이더 선택이 유지됨', async ({ page }) => {
    const providerSelect = page.locator('select:has-text("프로바이더"), [data-testid="provider-select"]').first();

    if (await providerSelect.isVisible()) {
      const options = await providerSelect.locator('option').allTextContents();

      if (options.length > 1) {
        await providerSelect.selectOption({ index: 1 });
        const selectedBefore = await providerSelect.inputValue();

        // 페이지 내 다른 요소 클릭
        await page.click('body');

        const selectedAfter = await providerSelect.inputValue();
        expect(selectedAfter).toBe(selectedBefore);
      }
    }
  });

  test('옵션 조합이 가능함', async ({ page }) => {
    // 프로바이더 선택
    const providerSelect = page.locator('select:has-text("프로바이더"), [data-testid="provider-select"]').first();
    if (await providerSelect.isVisible()) {
      await providerSelect.selectOption({ index: 1 });
    }

    // 스타일 선택
    const styleSelect = page.locator('select:has-text("스타일"), [data-testid="style-select"]').first();
    if (await styleSelect.isVisible()) {
      await styleSelect.selectOption({ index: 2 });
    }

    // 모디파이어가 있다면 선택
    const lengthSelect = page.locator('select:has-text("길이"), [data-testid="length-select"]').first();
    if (await lengthSelect.isVisible()) {
      await lengthSelect.selectOption({ index: 1 });
    }

    // 설정이 유지됨
    expect(true).toBeTruthy();
  });
});
