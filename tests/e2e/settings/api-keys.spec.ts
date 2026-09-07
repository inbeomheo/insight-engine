import { test, expect } from '../fixtures/test-fixtures';

// API 키 관리 제거 후의 계약: ChatMock 단일 서비스와 모델 선택만 제공한다.
test.describe('ChatMock 모델 설정 @parallel @no-auth', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test.beforeEach(async ({ page, mainPage }) => {
    await page.addInitScript(() => {
      localStorage.setItem('insight-engine-onboarding-done', 'true');
    });
    await mainPage.goto();
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();
  });

  test('고정 서비스를 안내하고 API 키 입력이나 서비스 선택을 노출하지 않는다', async ({ page }) => {
    const settings = page.getByRole('dialog', { name: '설정', exact: true });
    const service = settings.getByRole('group', { name: 'ChatMock 서비스 정보' });
    await expect(service).toContainText('ChatMock');
    await expect(service).toContainText('단일 AI 서비스 사용 중');
    await expect(settings.getByRole('combobox', { name: 'AI 모델 선택' })).toBeVisible();
    // 언어 선택은 별도로 존재한다. 서비스 선택 UI만 없어야 한다.
    await expect(settings.getByRole('combobox', { name: /서비스|provider/i })).toHaveCount(0);
    await expect(settings.getByLabel(/API.*키|API.*key/i)).toHaveCount(0);
    await expect(settings.getByPlaceholder(/API.*키|API.*key/i)).toHaveCount(0);
    // 비밀번호 입력은 계정 로그인용 하나만 존재해야 한다.
    await expect(settings.locator('input[type="password"]')).toHaveCount(1);
    await expect(settings.getByLabel('비밀번호', { exact: true })).toHaveAttribute('autocomplete', 'current-password');
  });

  test('선택한 ChatMock 모델을 새로고침 후에도 유지한다', async ({ page }) => {
    const settings = page.getByRole('dialog', { name: '설정', exact: true });
    await settings.getByRole('combobox', { name: 'AI 모델 선택' }).click();
    await page.getByRole('option', { name: 'GPT-5.5', exact: true }).click();
    await expect(settings.getByRole('combobox', { name: 'AI 모델 선택' })).toContainText('GPT-5.5');
    expect(await page.evaluate(() => JSON.parse(localStorage.getItem('insight-engine-selected-model') ?? 'null')))
      .toBe('chatmock/gpt-5.5');
    await page.reload();
    await page.getByRole('button', { name: '설정 열기', exact: true }).click();
    await expect(settings.getByRole('combobox', { name: 'AI 모델 선택' })).toContainText('GPT-5.5');
  });
});
