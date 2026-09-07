/**
 * 로컬 브라우저 검증의 초기 저장 상태를 준비한다.
 * 로그인 동작은 login.spec.ts가 요청과 세션 보존까지 별도로 검증한다.
 */
import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '../../test-results/auth/user.json');

setup('격리된 브라우저 상태 준비', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('dialog', { name: '환영합니다!' })).toBeVisible();
  // 운영 계정을 시도하거나 로그인 실패를 정상 결과로 저장하지 않는다.
  expect(await page.evaluate(() => localStorage.getItem('insight-engine-auth-session'))).toBeNull();
  await page.context().storageState({ path: authFile });
});
