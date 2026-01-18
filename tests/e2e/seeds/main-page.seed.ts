/**
 * 메인 페이지 Seed 파일
 *
 * 테스트 전에 페이지를 기본 상태로 설정
 */
import { test, expect } from '@playwright/test';

test('메인 페이지 초기화', async ({ page }) => {
  // 메인 페이지로 이동
  await page.goto('/');

  // 페이지 로드 완료 대기
  await page.waitForLoadState('networkidle');

  // localStorage 초기화 (선택적)
  await page.evaluate(() => {
    // 테스트에 영향을 줄 수 있는 항목만 제거
    localStorage.removeItem('pending_urls');
    localStorage.removeItem('draft_content');
  });

  // 페이지가 준비되었는지 확인
  await expect(page.locator('body')).toBeVisible();
});
