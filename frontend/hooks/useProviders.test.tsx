import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useProviders } from './useProviders';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  query: {
    data: undefined as undefined | {
      providers: Record<string, {
        name: string;
        api_base: string;
        models: Array<{
          id: string;
          name: string;
          max_input_tokens: number;
          price_input: number;
          price_output: number;
        }>;
      }>;
    },
    error: null as Error | null,
  },
  store: {
    selectedModel: '',
    setProviders: vi.fn(),
    setSelectedModel: vi.fn(),
  },
  toastError: vi.fn(),
}));

vi.mock('@tanstack/react-query', () => ({ useQuery: () => mocks.query }));
vi.mock('@/stores/settingsStore', () => ({ useSettingsStore: () => mocks.store }));
vi.mock('@/lib/api', () => ({ fetchProviders: vi.fn() }));
vi.mock('sonner', () => ({ toast: { error: mocks.toastError } }));

let root: Root | null = null;

function Harness() {
  useProviders();
  return null;
}

async function renderHook() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root!.render(<Harness />));
}

function providerFixture() {
  return {
    cliproxy: {
      name: 'OPEN AI',
      api_base: 'http://cli-proxy-api:8317/v1',
      models: [
        { id: 'cliproxy/gpt-5.6-sol', name: 'GPT-5.6 Sol', max_input_tokens: 128000, price_input: 0, price_output: 0 },
        { id: 'cliproxy/gpt-5.4', name: 'GPT-5.4', max_input_tokens: 128000, price_input: 0, price_output: 0 },
      ],
    },
    zai: {
      name: 'Z.AI',
      api_base: 'https://api.z.ai/api/coding/paas/v4',
      models: [
        { id: 'zai/glm-5.3-flash', name: 'GLM-5.3 Flash', max_input_tokens: 1000000, price_input: 0.15, price_output: 0.5 },
      ],
    },
  };
}

describe('useProviders 다중 provider 모델 동기화', () => {
  beforeEach(() => {
    mocks.query.data = undefined;
    mocks.query.error = null;
    mocks.store.selectedModel = '';
    vi.clearAllMocks();
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    root = null;
    document.body.innerHTML = '';
  });

  it('목록을 저장하고 유효하지 않은 선택을 첫 모델로 복구한다', async () => {
    const providers = providerFixture();
    mocks.query.data = { providers };
    mocks.store.selectedModel = 'chatmock/gpt-5.3-codex-spark';

    await renderHook();

    expect(mocks.store.setProviders).toHaveBeenCalledWith(providers);
    expect(mocks.store.setSelectedModel).toHaveBeenCalledWith('cliproxy/gpt-5.6-sol');
  });

  it('두 번째 provider의 GLM 모델 선택도 유효하게 유지한다', async () => {
    mocks.query.data = { providers: providerFixture() };
    mocks.store.selectedModel = 'zai/glm-5.3-flash';

    await renderHook();

    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
  });

  it('첫 provider가 비어도 다음 provider의 첫 모델을 선택한다', async () => {
    const providers = providerFixture();
    providers.cliproxy.models = [];
    mocks.query.data = { providers };

    await renderHook();

    expect(mocks.store.setSelectedModel).toHaveBeenCalledWith('zai/glm-5.3-flash');
  });

  it('모델이 없어도 빈 provider 목록 상태만 저장한다', async () => {
    mocks.query.data = { providers: {} };

    await renderHook();

    expect(mocks.store.setProviders).toHaveBeenCalledWith({});
    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
  });

  it('목록 조회 오류를 사용자에게 알린다', async () => {
    mocks.query.error = new Error('network');

    await renderHook();

    expect(mocks.toastError).toHaveBeenCalledWith('AI 모델 목록을 불러올 수 없습니다');
  });
});
