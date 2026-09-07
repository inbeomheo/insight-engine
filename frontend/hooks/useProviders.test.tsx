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
  setState: vi.fn(),
}));

vi.mock('@tanstack/react-query', () => ({ useQuery: () => mocks.query }));
vi.mock('@/stores/settingsStore', () => ({
  useSettingsStore: Object.assign(
    (selector: (state: typeof mocks.store) => unknown) => selector(mocks.store),
    { setState: mocks.setState },
  ),
}));
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

function cliProxyProviders() {
  return {
    cliproxyapi: {
      name: 'CLIProxyAPI',
      models: [
        { id: 'cliproxyapi/gpt-5.5', name: 'GPT-5.5', max_input_tokens: 128000, price_input: 0, price_output: 0 },
        { id: 'cliproxyapi/gpt-5.3-codex-spark', name: 'GPT-5.3 Codex Spark', max_input_tokens: 128000, price_input: 0, price_output: 0 },
      ],
    },
  };
}

describe('useProviders 단일 CLIProxyAPI 모델 동기화', () => {
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

  it('모델 순서와 관계없이 유효하지 않은 선택을 GPT-5.5로 메모리에서 복구한다', async () => {
    const providers = cliProxyProviders();
    providers.cliproxyapi.models.reverse();
    mocks.query.data = { providers };
    mocks.store.selectedModel = 'removed-model';

    await renderHook();

    expect(mocks.store.setProviders).toHaveBeenCalledWith(providers);
    expect(mocks.setState).toHaveBeenCalledWith({ selectedModel: 'cliproxyapi/gpt-5.5' });
    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
  });

  it.each(['gpt-5.5', 'gpt-5.3-codex-spark'])('ChatMock의 지원 모델 %s 선택은 메모리에서만 같은 모델로 연결한다', async (model) => {
    mocks.query.data = { providers: cliProxyProviders() };
    mocks.store.selectedModel = `chatmock/${model}`;

    await renderHook();

    expect(mocks.setState).toHaveBeenCalledWith({ selectedModel: `cliproxyapi/${model}` });
    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
  });

  it.each(['gpt-5.4-mini', 'gpt-5.4'])('지원이 종료된 ChatMock 모델 %s는 GPT-5.5로 복구한다', async (model) => {
    mocks.query.data = { providers: cliProxyProviders() };
    mocks.store.selectedModel = `chatmock/${model}`;

    await renderHook();

    expect(mocks.setState).toHaveBeenCalledWith({ selectedModel: 'cliproxyapi/gpt-5.5' });
    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
  });

  it('현재 모델이 유효하면 선택을 다시 저장하지 않는다', async () => {
    mocks.query.data = { providers: cliProxyProviders() };
    mocks.store.selectedModel = 'cliproxyapi/gpt-5.3-codex-spark';

    await renderHook();

    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
    expect(mocks.setState).not.toHaveBeenCalled();
  });

  it('기본 모델이 목록에 없으면 실제 제공되는 첫 모델을 선택한다', async () => {
    const providers = cliProxyProviders();
    providers.cliproxyapi.models = providers.cliproxyapi.models.slice(1);
    mocks.query.data = { providers };

    await renderHook();

    expect(mocks.setState).toHaveBeenCalledWith({ selectedModel: 'cliproxyapi/gpt-5.3-codex-spark' });
    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
  });

  it('저장된 선택값이 문자열이 아니어도 기본 모델을 사용한다', async () => {
    mocks.query.data = { providers: cliProxyProviders() };
    mocks.store.selectedModel = null as unknown as string;

    await renderHook();

    expect(mocks.setState).toHaveBeenCalledWith({ selectedModel: 'cliproxyapi/gpt-5.5' });
    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
  });

  it('모델이 없어도 빈 provider 목록 상태만 저장한다', async () => {
    mocks.query.data = { providers: {} };

    await renderHook();

    expect(mocks.store.setProviders).toHaveBeenCalledWith({});
    expect(mocks.store.setSelectedModel).not.toHaveBeenCalled();
    expect(mocks.setState).not.toHaveBeenCalled();
  });

  it('목록 조회 오류를 사용자에게 알린다', async () => {
    mocks.query.error = new Error('network');

    await renderHook();

    expect(mocks.toastError).toHaveBeenCalledWith('AI 모델 목록을 불러올 수 없습니다');
  });
});
