import { test, expect } from '../fixtures/test-fixtures';

test.describe('DeepSeek 프로바이더', () => {
  test('프로바이더 목록에 DeepSeek가 표시된다', async ({ page }) => {
    const response = await page.request.get('/api/providers');
    const data = await response.json();

    // providers는 객체 (key: provider_id)
    expect(data.providers).toBeDefined();
    expect(data.providers.deepseek).toBeDefined();
    expect(data.providers.deepseek.name).toBe('DeepSeek');
  });

  test('DeepSeek 프로바이더에 올바른 모델이 포함되어 있다', async ({ page }) => {
    const response = await page.request.get('/api/providers');
    const data = await response.json();

    const deepseek = data.providers.deepseek;
    expect(deepseek.models.length).toBeGreaterThan(0);

    const modelIds = deepseek.models.map((m: { id: string }) => m.id);
    expect(modelIds).toContain('deepseek/deepseek-chat');
    expect(modelIds).toContain('deepseek/deepseek-reasoner');
  });
});
