import { randomUUID } from 'node:crypto';
import { test, expect } from '../fixtures/test-fixtures';

const AUTH_KEY = 'insight-engine-auth-session';

test.describe('설정의 계정 인증 @parallel @no-auth', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test.beforeEach(async ({ page, mainPage }) => {
    await page.addInitScript(() => {
      localStorage.setItem('insight-engine-onboarding-done', 'true');
    });
    // 개인 기능의 외부 저장소 요청은 테스트 브라우저에서 종료한다.
    await page.route('**/api/workspaces', route => route.fulfill({ json: { workspaces: [] } }));
    await page.route('**/api/user/style-memory', route => route.fulfill({
      status: 503, json: { error: '테스트에서는 개인 저장소를 연결하지 않습니다.' },
    }));
    await mainPage.goto();
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();
    await expect(page.getByRole('dialog', { name: '설정', exact: true })).toBeVisible();
  });

  test('이메일과 비밀번호를 모두 입력해야 로그인할 수 있다', async ({ page }) => {
    const settings = page.getByRole('dialog', { name: '설정', exact: true });
    const login = settings.getByRole('button', { name: '로그인', exact: true });
    await expect(settings.getByRole('heading', { name: '계정', exact: true })).toBeVisible();
    await expect(settings.getByLabel('이메일', { exact: true })).toBeVisible();
    await expect(settings.getByLabel('비밀번호', { exact: true })).toHaveAttribute('type', 'password');
    await expect(login).toBeDisabled();
    await settings.getByLabel('이메일', { exact: true }).fill('browser-test@example.invalid');
    await expect(login).toBeDisabled();
    await settings.getByLabel('비밀번호', { exact: true }).fill(randomUUID());
    await expect(login).toBeEnabled();
  });

  test('로그인 응답에서 갱신 토큰을 제외하고 저장하며 로그아웃 시 세션을 비운다', async ({ page }) => {
    const email = 'browser-test@example.invalid';
    const password = randomUUID();
    const accessToken = randomUUID();
    const userId = randomUUID();
    const expiresAt = Math.floor(Date.now() / 1000) + 3600;
    await page.route('**/api/auth/login', async route => {
      expect(route.request().method()).toBe('POST');
      expect(route.request().postDataJSON()).toEqual({ email, password });
      expect(route.request().headers()['x-auth-transport']).toBe('cookie');
      await route.fulfill({ json: {
        user: { id: userId, email },
        session: { access_token: accessToken, refresh_token: randomUUID(), expires_at: expiresAt },
      } });
    });
    let logoutCalls = 0;
    await page.route('**/api/auth/logout', async route => {
      logoutCalls += 1;
      expect(route.request().method()).toBe('POST');
      expect(route.request().headers().authorization).toBe('Bearer ' + accessToken);
      await route.fulfill({ json: { success: true } });
    });
    const settings = page.getByRole('dialog', { name: '설정', exact: true });
    await settings.getByLabel('이메일', { exact: true }).fill(email);
    await settings.getByLabel('비밀번호', { exact: true }).fill(password);
    await settings.getByRole('button', { name: '로그인', exact: true }).click();
    await expect(settings.getByText(email, { exact: true })).toBeVisible();
    await expect(settings.getByText('인증됨', { exact: true })).toBeVisible();
    await expect.poll(() => page.evaluate(key => JSON.parse(localStorage.getItem(key) ?? 'null'), AUTH_KEY))
      .toEqual({ user: { id: userId, email }, session: { access_token: accessToken, expires_at: expiresAt } });

    await page.reload();
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();
    await expect(settings.getByText(email, { exact: true })).toBeVisible();
    await settings.getByRole('button', { name: '로그아웃', exact: true }).click();
    await expect(settings.getByLabel('이메일', { exact: true })).toBeVisible();
    await expect(settings.getByRole('button', { name: '로그인', exact: true })).toBeDisabled();
    await expect.poll(() => page.evaluate(key => localStorage.getItem(key), AUTH_KEY)).toBeNull();
    expect(logoutCalls).toBe(1);
  });

  test('인증 실패 메시지를 표시하고 로그인 상태를 만들지 않는다', async ({ page }) => {
    await page.route('**/api/auth/login', route => route.fulfill({
      status: 401, json: { error: '이메일 또는 비밀번호가 올바르지 않습니다.' },
    }));
    const settings = page.getByRole('dialog', { name: '설정', exact: true });
    await settings.getByLabel('이메일', { exact: true }).fill('browser-test@example.invalid');
    await settings.getByLabel('비밀번호', { exact: true }).fill(randomUUID());
    await settings.getByRole('button', { name: '로그인', exact: true }).click();
    await expect(page.getByText('이메일 또는 비밀번호가 올바르지 않습니다.', { exact: true })).toBeVisible();
    await expect(settings.getByRole('button', { name: '로그인', exact: true })).toBeEnabled();
    await expect(settings.getByRole('button', { name: '로그아웃', exact: true })).toHaveCount(0);
    expect(await page.evaluate(key => localStorage.getItem(key), AUTH_KEY)).toBeNull();
  });
});
