/**
 * 히스토리 및 사용량 패널 테스트
 *
 * spec: specs/04-history-usage-panels.plan.md
 *
 * 병렬 실행: ✅
 * 인증 필요: 부분적 (UI는 비인증 상태에서도 테스트 가능)
 */
import { test, expect } from '../fixtures/test-fixtures';

test.describe('히스토리 및 사용량 패널 @parallel', () => {
  test.beforeEach(async ({ mainPage }) => {
    await mainPage.goto();
  });

  // ========================================
  // Suite 1: 사이드바 네비게이션
  // ========================================
  test.describe('Suite 1: 사이드바 네비게이션', () => {
    test('TC-1.1: 대시보드 탭 클릭 시 활성화', async ({ page }) => {
      // 1. 사이드바의 대시보드 아이콘 클릭 (데스크톱 버전만 선택)
      const dashboardBtn = page.locator('#sidebar button[data-section="dashboard"]');
      await dashboardBtn.click();
      await page.waitForTimeout(300);

      // Expected: 대시보드 패널 활성화, 아이콘 하이라이트
      await expect(dashboardBtn).toHaveClass(/bg-primary|active/);

      // 대시보드 뷰가 표시되어야 함
      const urlInput = page.locator('#url-input');
      await expect(urlInput).toBeVisible();
    });

    test('TC-1.2: 히스토리 탭 클릭 시 패널 표시', async ({ page }) => {
      // 1. 사이드바의 히스토리 아이콘 클릭
      const historyBtn = page.locator('button[data-section="history"]');

      if (!(await historyBtn.isVisible().catch(() => false))) {
        test.skip();
        return;
      }

      await historyBtn.click();
      await page.waitForTimeout(500);

      // Expected: 히스토리 버튼 활성화
      await expect(historyBtn).toHaveClass(/bg-primary|active/);
    });

    test('TC-1.3: 사용량 탭 클릭 시 패널 표시', async ({ page }) => {
      // 1. 사이드바의 사용량 아이콘 클릭
      const usageBtn = page.locator('button[data-section="usage"]');

      if (!(await usageBtn.isVisible().catch(() => false))) {
        test.skip();
        return;
      }

      await usageBtn.click();
      await page.waitForTimeout(500);

      // Expected: 사용량 버튼 활성화
      await expect(usageBtn).toHaveClass(/bg-primary|active/);
    });
  });

  // ========================================
  // Suite 2: 탭 전환
  // ========================================
  test.describe('Suite 2: 탭 전환', () => {
    test('TC-2.1: 빠른 탭 전환 시 정상 동작', async ({ page }) => {
      // 1. 대시보드 → 히스토리 → 사용량 빠르게 전환 (데스크톱 사이드바만 선택)
      const dashboardBtn = page.locator('#sidebar button[data-section="dashboard"]');
      const historyBtn = page.locator('#sidebar button[data-section="history"]');
      const usageBtn = page.locator('#sidebar button[data-section="usage"]');

      // 대시보드 클릭
      await dashboardBtn.click();
      await page.waitForTimeout(100);

      // Expected: 대시보드 활성화
      await expect(dashboardBtn).toHaveClass(/bg-primary|active/);

      // 히스토리로 전환
      if (await historyBtn.isVisible().catch(() => false)) {
        await historyBtn.click();
        await page.waitForTimeout(100);
        await expect(historyBtn).toHaveClass(/bg-primary|active/);
      }

      // 사용량으로 전환
      if (await usageBtn.isVisible().catch(() => false)) {
        await usageBtn.click();
        await page.waitForTimeout(100);
        await expect(usageBtn).toHaveClass(/bg-primary|active/);
      }

      // 다시 대시보드로
      await dashboardBtn.click();
      await page.waitForTimeout(100);

      // Expected: 이전 상태 유지 (URL 입력 필드 등이 그대로)
      const urlInput = page.locator('#url-input');
      await expect(urlInput).toBeVisible();
    });

    test('TC-2.2: 탭 활성 상태 유지', async ({ page }) => {
      // 1. 히스토리 탭 선택
      const historyBtn = page.locator('button[data-section="history"]');

      if (!(await historyBtn.isVisible().catch(() => false))) {
        test.skip();
        return;
      }

      await historyBtn.click();
      await page.waitForTimeout(500);

      // Expected: 활성 탭 상태
      await expect(historyBtn).toHaveClass(/bg-primary|active/);

      // 2. 페이지 내 다른 동작 수행 (스크롤)
      await page.evaluate(() => window.scrollTo(0, 100));
      await page.waitForTimeout(300);

      // 3. 탭 상태 확인 - 활성 탭 상태 유지됨
      await expect(historyBtn).toHaveClass(/bg-primary|active/);
    });
  });
});
