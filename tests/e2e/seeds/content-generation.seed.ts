/**
 * 콘텐츠 생성 테스트용 Seed 파일
 *
 * 콘텐츠 생성 테스트 전에 필요한 상태를 설정
 */
import { test, expect } from '@playwright/test';

test('콘텐츠 생성 테스트 준비', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('networkidle');

  // 이전 생성 결과 초기화
  await page.evaluate(() => {
    localStorage.removeItem('generated_content');
    localStorage.removeItem('generation_history');
  });

  // 페이지가 준비되었는지 확인
  const urlInput = page.locator('input[placeholder*="YouTube"], [data-testid="url-input"]');
  await expect(urlInput).toBeVisible();
});
