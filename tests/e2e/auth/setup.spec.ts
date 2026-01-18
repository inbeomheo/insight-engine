/**
 * 인증 Setup 테스트
 *
 * 다른 인증 필요 테스트의 의존성으로 사용됨
 * 이 테스트가 먼저 실행되어 storageState를 저장함
 */
import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '../.auth/user.json');

setup('인증 상태 준비', async ({ page }) => {
  // 테스트 환경에서 인증 필요 여부 확인
  await page.goto('/');

  // 로그인 버튼/링크 확인
  const loginLink = page.locator('a:has-text("로그인"), button:has-text("로그인")');
  const isAuthRequired = await loginLink.isVisible().catch(() => false);

  if (!isAuthRequired) {
    // 인증이 필요 없는 환경 (Supabase 비활성화)
    console.log('인증이 비활성화된 환경입니다. Setup 스킵.');

    // 빈 storageState 저장
    await page.context().storageState({ path: authFile });
    return;
  }

  // 로그인 페이지로 이동
  await loginLink.click();
  await page.waitForURL('**/login**', { timeout: 5000 }).catch(() => {});

  // 테스트 계정으로 로그인 (환경 변수에서 가져옴)
  const testEmail = process.env.TEST_USER_EMAIL || 'test@example.com';
  const testPassword = process.env.TEST_USER_PASSWORD || 'testpassword123';

  await page.fill('input[type="email"], [data-testid="email-input"]', testEmail);
  await page.fill('input[type="password"], [data-testid="password-input"]', testPassword);
  await page.click('button:has-text("로그인"), [data-testid="login-button"]');

  // 로그인 성공 대기
  await page.waitForURL('/', { timeout: 10000 }).catch(async () => {
    // 로그인 실패 시 에러 확인
    const error = await page.locator('.error, [role="alert"]').textContent().catch(() => null);
    if (error) {
      console.log('로그인 실패:', error);
    }
  });

  // 인증 상태 저장
  await page.context().storageState({ path: authFile });
});
