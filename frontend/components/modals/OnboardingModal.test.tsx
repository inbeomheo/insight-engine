import { act, type ReactNode } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import OnboardingModal from './OnboardingModal';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const mocks = vi.hoisted(() => ({
  setOnboardingDone: vi.fn(),
  ui: {
    activeModal: 'onboarding',
    setOnboardingOpen: vi.fn(),
  },
  settings: {
    providers: {} as Record<string, { name: string; models: Array<{ id: string }> }>,
  },
}));

vi.mock('@/stores/uiStore', () => ({
  useUIStore: (selector?: (state: typeof mocks.ui) => unknown) => selector ? selector(mocks.ui) : mocks.ui,
}));
vi.mock('@/stores/settingsStore', () => ({
  useSettingsStore: (selector?: (state: typeof mocks.settings) => unknown) => selector ? selector(mocks.settings) : mocks.settings,
}));
vi.mock('@/lib/storage', () => ({ setOnboardingDone: mocks.setOnboardingDone }));
vi.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// onOpenChange(false)를 눌러볼 수 있게 노출한다 — X / Esc / 오버레이 클릭이 모두 이 경로다.
vi.mock('@/components/ui/dialog', () => ({
  Dialog: ({ children, onOpenChange }: { children: ReactNode; onOpenChange?: (open: boolean) => void }) => (
    <>
      <button aria-label="테스트 닫기" onClick={() => onOpenChange?.(false)}>close</button>
      {children}
    </>
  ),
  DialogContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: ReactNode }) => <h1>{children}</h1>,
  DialogDescription: ({ children }: { children: ReactNode }) => <p>{children}</p>,
}));
vi.mock('@/components/ui/button', () => ({
  Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
    <button {...props}>{children}</button>
  ),
}));

let root: Root | null = null;

async function render(component: ReactNode) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root!.render(component));
  return container;
}

describe('온보딩 모달 잠금 회귀 방어', () => {
  beforeEach(() => {
    mocks.ui.activeModal = 'onboarding';
    mocks.settings.providers = {};
    vi.clearAllMocks();
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    root = null;
    document.body.innerHTML = '';
  });

  it('모델 목록 조회 실패 후에도 시작 버튼으로 안내를 닫을 수 있다', async () => {
    const view = await render(<OnboardingModal />);
    const start = Array.from(view.querySelectorAll('button'))
      .find((b) => b.textContent?.includes('onboarding.start'));
    expect(start).toBeDefined();
    expect(start!.disabled).toBe(false);
    await act(async () => start?.click());
    expect(mocks.setOnboardingDone).toHaveBeenCalledOnce();
    expect(mocks.ui.setOnboardingOpen).toHaveBeenCalledWith(false);
  });

  it('사용 가능한 모델이 있을 때 시작 버튼으로 완료할 수 있다', async () => {
    mocks.settings.providers = {
      cliproxyapi: {
        name: 'CLIProxyAPI',
        models: [{ id: 'cliproxyapi/test-model' }],
      },
    };
    const view = await render(<OnboardingModal />);
    const start = Array.from(view.querySelectorAll<HTMLButtonElement>('button'))
      .find((button) => button.textContent?.includes('onboarding.start'));

    expect(start?.disabled).toBe(false);
    await act(async () => start?.click());
    expect(mocks.setOnboardingDone).toHaveBeenCalledOnce();
    expect(mocks.ui.setOnboardingOpen).toHaveBeenCalledWith(false);
  });

  it('X / Esc / 오버레이로 닫아도 완료로 기록한다', async () => {
    const view = await render(<OnboardingModal />);
    await act(async () => view.querySelector<HTMLButtonElement>('[aria-label="테스트 닫기"]')?.click());

    // 이 기록이 없으면 새로고침마다 모달이 다시 떠 앱이 잠긴다.
    expect(mocks.setOnboardingDone).toHaveBeenCalledOnce();
    expect(mocks.ui.setOnboardingOpen).toHaveBeenCalledWith(false);
  });

  it('열려 있는 상태를 유지할 때는 완료로 기록하지 않는다', async () => {
    await render(<OnboardingModal />);
    expect(mocks.setOnboardingDone).not.toHaveBeenCalled();
  });
});
