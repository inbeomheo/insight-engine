import { act, type ReactNode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OnboardingModal from '@/components/modals/OnboardingModal';
import SettingsModal from './SettingsModal';
import SettingsPopover from './SettingsPopover';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  setOnboardingDone: vi.fn(),
  ui: {
    activeModal: 'onboarding',
    settingsPopoverOpen: false,
    setOnboardingOpen: vi.fn(),
    setSettingsModalOpen: vi.fn(),
    setSettingsPopoverOpen: vi.fn(),
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
    selectedStyle: 'summary',
    modifiers: {
      length: 'medium',
      writing_style: 'conversational',
      language: 'ko',
    },
    customStyles: [],
    webhookUrl: '',
    enableWebSearch: false,
    transcriptLanguage: null,
    setSelectedModel: vi.fn(),
    setSelectedStyle: vi.fn(),
    setModifiers: vi.fn(),
    setWebhookUrl: vi.fn(),
    setEnableWebSearch: vi.fn(),
    setTranscriptLanguage: vi.fn(),
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
      'onboarding.serviceCount': `${values?.count ?? 0}개 AI 서비스`,
      'onboarding.serviceInfoLabel': 'AI 서비스 정보',
      'onboarding.noModels': '사용 가능한 AI 모델이 없습니다',
      'onboarding.noServer': 'AI 서버에 연결할 수 없습니다',
      'onboarding.start': '시작',
      'settings.title': '설정',
      'settings.aiServiceDescription': 'AI 서비스 설정',
      'settings.aiService': 'AI 서비스',
      'settings.serviceInfoLabel': 'AI 서비스 정보',
      'settings.multiServiceActive': `${values?.count ?? 0}개 AI 서비스 사용 중`,
      'settings.singleServiceActive': '단일 AI 서비스 사용 중',
      'settings.modelSelectLabel': 'AI 모델 선택',
      'settings.noModels': '사용 가능한 AI 모델이 없습니다',
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
      <button type="button" aria-label="테스트 모델 변경" onClick={() => onValueChange('zai/glm-5.3-flash')}>
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
  testWebhook: vi.fn(),
  getStyleMemory: vi.fn(() => new Promise(() => undefined)),
  updateStyleMemory: vi.fn(),
  resetStyleMemory: vi.fn(),
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock('./LanguageSwitcher', () => ({ default: () => <div>언어 전환</div> }));
vi.mock('./KnowledgeManager', () => ({ default: () => <div>지식 관리</div> }));

let root: Root | null = null;
let container: HTMLDivElement | null = null;

async function render(component: ReactNode) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root!.render(component));
  return container;
}

function setMultiProvider() {
  mocks.settings.providers = {
    cliproxy: {
      name: 'OPEN AI',
      api_base: 'http://cli-proxy-api:8317/v1',
      models: [
        { id: 'cliproxy/gpt-5.6-sol', name: 'GPT-5.6 Sol', max_input_tokens: 128000, price_input: 0, price_output: 0 },
        { id: 'cliproxy/gpt-5.5', name: 'GPT-5.5', max_input_tokens: 128000, price_input: 0, price_output: 0 },
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
  mocks.settings.selectedModel = 'cliproxy/gpt-5.6-sol';
}

function findButton(view: HTMLElement, text: string) {
  return Array.from(view.querySelectorAll('button')).find((button) => button.textContent?.includes(text));
}

describe('다중 AI 서비스 UI', () => {
  beforeEach(() => {
    mocks.ui.activeModal = 'onboarding';
    mocks.ui.settingsPopoverOpen = false;
    mocks.settings.providers = {};
    mocks.settings.selectedModel = '';
    vi.clearAllMocks();
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    root = null;
    container?.remove();
    container = null;
    document.body.innerHTML = '';
  });

  it('온보딩에서 모든 서비스와 전체 모델 수를 보여주고 시작 동작을 유지한다', async () => {
    setMultiProvider();
    const view = await render(<OnboardingModal />);

    expect(view.querySelector('[aria-label="AI 서비스 정보"]')?.textContent)
      .toContain('OPEN AI · Z.AI');
    expect(view.textContent).toContain('2개 AI 서비스 · 3개 모델');
    expect(view.querySelectorAll('h1')).toHaveLength(1);
    expect(view.querySelector('[aria-label*="프로바이더 선택"]')).toBeNull();

    const startButton = findButton(view, '시작');
    expect(startButton?.disabled).toBe(false);
    await act(async () => startButton?.click());
    expect(mocks.setOnboardingDone).toHaveBeenCalledOnce();
    expect(mocks.ui.setOnboardingOpen).toHaveBeenCalledWith(false);
  });

  it('온보딩에서 서비스가 없으면 시작을 막는다', async () => {
    const view = await render(<OnboardingModal />);
    expect(view.textContent).toContain('AI 서버에 연결할 수 없습니다');
    expect(findButton(view, '시작')?.disabled).toBe(true);
  });

  it('온보딩에서 모델이 없으면 안내하고 시작을 막는다', async () => {
    setMultiProvider();
    for (const provider of Object.values(mocks.settings.providers)) {
      provider.models = [];
    }
    const view = await render(<OnboardingModal />);

    expect(view.textContent).toContain('사용 가능한 AI 모델이 없습니다');
    expect(findButton(view, '시작')?.disabled).toBe(true);
  });

  it('설정에서 두 서비스의 모든 모델을 하나의 선택기로 제공한다', async () => {
    mocks.ui.activeModal = 'settings';
    setMultiProvider();
    const view = await render(<SettingsModal />);

    expect(view.querySelector('[aria-label="AI 서비스 정보"]')?.textContent)
      .toContain('2개 AI 서비스 사용 중');
    expect(view.querySelector('[aria-label="AI 모델 선택"]')).not.toBeNull();
    expect(view.querySelectorAll('[data-testid="select-control"]')).toHaveLength(1);
    expect(view.textContent).toContain('GPT-5.6 Sol');
    expect(view.textContent).toContain('GLM-5.3 Flash');

    await act(async () => view.querySelector<HTMLButtonElement>('[aria-label="테스트 모델 변경"]')?.click());
    expect(mocks.settings.setSelectedModel).toHaveBeenCalledWith('zai/glm-5.3-flash');
  });

  it('입력창 설정도 모든 서비스 모델을 보여주고 저장된 GLM 선택을 유지한다', async () => {
    mocks.ui.settingsPopoverOpen = true;
    setMultiProvider();
    mocks.settings.selectedModel = 'zai/glm-5.3-flash';
    const view = await render(<SettingsPopover />);

    expect(view.textContent).toContain('OPEN AI · Z.AI');
    expect(view.textContent).toContain('GPT-5.6 Sol');
    expect(view.textContent).toContain('GLM-5.3 Flash');
    expect(view.querySelector('[data-testid="select-control"]')?.getAttribute('data-value'))
      .toBe('zai/glm-5.3-flash');
  });

  it('저장된 모델이 유효하지 않아도 첫 모델로 복구한다', async () => {
    mocks.ui.activeModal = 'settings';
    setMultiProvider();
    mocks.settings.selectedModel = 'chatmock/gpt-5.3-codex-spark';
    const view = await render(<SettingsModal />);

    expect(view.querySelector('[aria-label="AI 서비스 정보"]')?.textContent)
      .toContain('OPEN AI · Z.AI');
    expect(view.querySelector('[data-testid="select-control"]')?.getAttribute('data-value'))
      .toBe('cliproxy/gpt-5.6-sol');
  });

  it('설정에서 모델이 없으면 빈 선택기 대신 안내를 보여준다', async () => {
    mocks.ui.activeModal = 'settings';
    setMultiProvider();
    for (const provider of Object.values(mocks.settings.providers)) {
      provider.models = [];
    }
    const view = await render(<SettingsModal />);

    expect(view.textContent).toContain('사용 가능한 AI 모델이 없습니다');
    expect(view.querySelector('[data-testid="select-control"]')).toBeNull();
  });

  it('설정에서 서비스가 없으면 사용 불가 안내를 보여준다', async () => {
    mocks.ui.activeModal = 'settings';
    const view = await render(<SettingsModal />);
    expect(view.textContent).toContain('사용 가능한 AI 서비스가 없습니다');
    expect(view.querySelector('[data-testid="select-control"]')).toBeNull();
  });
});
