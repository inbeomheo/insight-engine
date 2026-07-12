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

function chatMockProviders() {
  return {
    chatmock: {
      name: 'ChatMock',
      api_base: 'http://127.0.0.1:8000/v1',
      models: [
        { id: 'chatmock/gpt-5.4-mini', name: 'GPT-5.4 Mini', max_input_tokens: 128000, price_input: 0, price_output: 0 },
        { id: 'chatmock/gpt-5.4', name: 'GPT-5.4', max_input_tokens: 128000, price_input: 0, price_output: 0 },
      ],
    },
  };
}

describe('useProviders 단일 ChatMock 모델 동기화', () => {
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

  it('모델 목록을 저장하고 유효하지 않은 선택을 첫 모델로 복구한다', async () => {
    const providers = chatMockProviders();
    mocks.query.data = { providers };
    mocks.store.selectedModel = 'removed-model';

    await renderHook();

    expect(mocks.store.setProviders).toHaveBeenCalledWith(providers);
    expect(mocks.store.setSelectedModel).toHaveBeenCalledWith('chatmock/gpt-5.4-mini');
  });

  it('현재 모델이 유효하면 선택을 다시 저장하지 않는다', async () => {
    mocks.query.data = { providers: chatMockProviders() };
    mocks.store.selectedModel = 'chatmock/gpt-5.4';

    await renderHook();

    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
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