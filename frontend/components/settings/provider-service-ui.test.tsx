import { act, type ReactNode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OnboardingModal from '@/components/modals/OnboardingModal';
import SettingsModal from './SettingsModal';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  setOnboardingDone: vi.fn(),
  ui: {
    activeModal: 'onboarding',
    setOnboardingOpen: vi.fn(),
    setSettingsModalOpen: vi.fn(),
  },
  settings: {
    providers: {} as Record<string, {
      name: string;
      api_base: string;
      models: Array<{
        id: string;
        name: string;
        max_input_tokens: number;
        price_input: number;
        price_output: number;
      }>;
    }>,
    selectedModel: '',
    setSelectedModel: vi.fn(),
  },
}));

vi.mock('@/stores/uiStore', () => ({ useUIStore: () => mocks.ui }));
vi.mock('@/stores/settingsStore', () => ({ useSettingsStore: () => mocks.settings }));
vi.mock('@/lib/storage', () => ({ setOnboardingDone: mocks.setOnboardingDone }));
vi.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string, values?: { count?: number }) => ({
      'onboarding.title': '시작하기',
      'onboarding.description': '학습을 시작하세요',
      'onboarding.modelCount': `${values?.count ?? 0}개 모델`,
      'onboarding.serviceInfoLabel': 'ChatMock 서비스 정보',
      'onboarding.singleService': '단일 AI 서비스',
      'onboarding.noModels': '사용 가능한 ChatMock 모델이 없습니다',
      'onboarding.noServer': 'AI 서버에 연결할 수 없습니다',
      'onboarding.start': '시작',
      'settings.title': '설정',
      'settings.aiServiceDescription': 'AI 서비스 설정',
      'settings.aiService': 'AI 서비스',
      'settings.serviceInfoLabel': 'ChatMock 서비스 정보',
      'settings.singleServiceActive': '단일 AI 서비스 사용 중',
      'settings.modelSelectLabel': 'AI 모델 선택',
      'settings.noModels': '사용 가능한 ChatMock 모델이 없습니다',
      'settings.noProviders': '사용 가능한 AI 서비스가 없습니다',
      'settings.selectModel': '모델 선택',
      'language.label': '언어',
      'settings.cacheManagement': '캐시 관리',
      'settings.cacheDescription': '캐시 설명',
      'settings.clearCache': '캐시 비우기',
    }[key] ?? key),
  }),
}));
vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children }: { children: ReactNode }) => <>{children}</>,
  DialogContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: ReactNode }) => <h1>{children}</h1>,
  DialogDescription: ({ children }: { children: ReactNode }) => <p>{children}</p>,
}));
vi.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    variant,
    size,
    ...props
  }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string; size?: string }) => (
    <button data-variant={variant} data-size={size} {...props}>{children}</button>
  ),
}));
vi.mock('@/components/ui/select', () => ({
  Select: ({
    children,
    value,
    onValueChange,
  }: {
    children: ReactNode;
    value: string;
    onValueChange: (value: string) => void;
  }) => (
    <div data-testid="select-control" data-value={value}>
      <button type="button" aria-label="테스트 모델 변경" onClick={() => onValueChange('chatmock/gpt-5.4')}>
        모델 변경
      </button>
      {children}
    </div>
  ),
  SelectContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  SelectItem: ({ children, value }: { children: ReactNode; value: string }) => (
    <div data-value={value}>{children}</div>
  ),
  SelectTrigger: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
  SelectValue: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
}));
vi.mock('@/lib/api', () => ({
  clearCache: vi.fn(),
  getStyleMemory: vi.fn(() => new Promise(() => undefined)),
  updateStyleMemory: vi.fn(),
  resetStyleMemory: vi.fn(),
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock('./LanguageSwitcher', () => ({ default: () => <div>언어 전환</div> }));

let root: Root | null = null;
let container: HTMLDivElement | null = null;

async function render(component: ReactNode) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root!.render(component));
  return container;
}

function setChatMockProvider() {
  mocks.settings.providers = {
    chatmock: {
      name: 'ChatMock (OpenAI 호환)',
      api_base: 'http://127.0.0.1:8000/v1',
      models: [
        { id: 'chatmock/gpt-5.4-mini', name: 'GPT-5.4 Mini', max_input_tokens: 128000, price_input: 0, price_output: 0 },
        { id: 'chatmock/gpt-5.4', name: 'GPT-5.4', max_input_tokens: 128000, price_input: 0, price_output: 0 },
      ],
    },
  };
  mocks.settings.selectedModel = 'chatmock/gpt-5.4-mini';
}

function findButton(view: HTMLElement, text: string) {
  return Array.from(view.querySelectorAll('button')).find((button) => button.textContent?.includes(text));
}

describe('단일 ChatMock 서비스 UI', () => {
  beforeEach(() => {
    mocks.ui.activeModal = 'onboarding';
    mocks.settings.providers = {};
    mocks.settings.selectedModel = '';
    vi.clearAllMocks();
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    root = null;
    container = null;
    document.body.innerHTML = '';
  });

  it('온보딩에서 고정 서비스 정보를 보여주고 시작 동작을 유지한다', async () => {
    setChatMockProvider();
    const view = await render(<OnboardingModal />);

    expect(view.querySelector('[aria-label="ChatMock 서비스 정보"]')?.textContent)
      .toContain('ChatMock (OpenAI 호환)');
    expect(view.textContent).toContain('단일 AI 서비스 · 2개 모델');
    expect(view.querySelector('[aria-label*="프로바이더 선택"]')).toBeNull();

    const startButton = findButton(view, '시작');
    expect(startButton?.disabled).toBe(false);
    await act(async () => startButton?.click());
    expect(mocks.setOnboardingDone).toHaveBeenCalledOnce();
    expect(mocks.ui.setOnboardingOpen).toHaveBeenCalledWith(false);
  });

  it('온보딩에서 서비스가 없으면 안내하되 시작을 막지 않는다', async () => {
    const view = await render(<OnboardingModal />);
    expect(view.textContent).toContain('AI 서버에 연결할 수 없습니다');

    // 모델 목록을 못 불러와도 진입은 가능해야 한다.
    // 막아버리면 setOnboardingDone()이 영영 호출되지 않아 매 방문마다 모달이 다시 뜬다.
    const startButton = findButton(view, '시작');
    expect(startButton?.disabled).toBe(false);
    await act(async () => startButton?.click());
    expect(mocks.setOnboardingDone).toHaveBeenCalledOnce();
    expect(mocks.ui.setOnboardingOpen).toHaveBeenCalledWith(false);
  });

  it('온보딩에서 모델이 없으면 안내하되 시작을 막지 않는다', async () => {
    setChatMockProvider();
    mocks.settings.providers.chatmock.models = [];
    const view = await render(<OnboardingModal />);

    expect(view.textContent).toContain('사용 가능한 ChatMock 모델이 없습니다');

    const startButton = findButton(view, '시작');
    expect(startButton?.disabled).toBe(false);
    await act(async () => startButton?.click());
    expect(mocks.setOnboardingDone).toHaveBeenCalledOnce();
  });

  it('설정에서 서비스 정보와 단일 모델 선택 동작만 제공한다', async () => {
    mocks.ui.activeModal = 'settings';
    setChatMockProvider();
    const view = await render(<SettingsModal />);

    expect(view.querySelector('[aria-label="ChatMock 서비스 정보"]')?.textContent)
      .toContain('단일 AI 서비스 사용 중');
    expect(view.querySelector('[aria-label="AI 모델 선택"]')).not.toBeNull();
    expect(view.querySelectorAll('[data-testid="select-control"]')).toHaveLength(1);
    expect(view.textContent).toContain('GPT-5.4 Mini');

    await act(async () => view.querySelector<HTMLButtonElement>('[aria-label="테스트 모델 변경"]')?.click());
    expect(mocks.settings.setSelectedModel).toHaveBeenCalledWith('chatmock/gpt-5.4');
  });

  it('\uc800\uc7a5\ub41c \ubaa8\ub378\uc774 \uc720\ud6a8\ud558\uc9c0 \uc54a\uc544\ub3c4 \uccab ChatMock \ubaa8\ub378\ub85c \ubcf5\uad6c\ud55c\ub2e4', async () => {
    mocks.ui.activeModal = 'settings';
    setChatMockProvider();
    mocks.settings.selectedModel = 'removed-model';
    const view = await render(<SettingsModal />);

    expect(view.querySelector('[aria-label="ChatMock 서비스 정보"]')?.textContent)
      .toContain('ChatMock (OpenAI 호환)');
    expect(view.querySelector('[data-testid="select-control"]')?.getAttribute('data-value'))
      .toBe('chatmock/gpt-5.4-mini');
  });

  it('설정에서 모델이 없으면 빈 선택기 대신 안내를 보여준다', async () => {
    mocks.ui.activeModal = 'settings';
    setChatMockProvider();
    mocks.settings.providers.chatmock.models = [];
    const view = await render(<SettingsModal />);

    expect(view.textContent).toContain('사용 가능한 ChatMock 모델이 없습니다');
    expect(view.querySelector('[data-testid="select-control"]')).toBeNull();
  });

  it('설정에서 서비스가 없으면 사용 불가 안내를 보여준다', async () => {
    mocks.ui.activeModal = 'settings';
    const view = await render(<SettingsModal />);
    expect(view.textContent).toContain('사용 가능한 AI 서비스가 없습니다');
    expect(view.querySelector('[data-testid="select-control"]')).toBeNull();
  });
});
