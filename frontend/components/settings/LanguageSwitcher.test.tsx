import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';
import LanguageSwitcher from './LanguageSwitcher';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

vi.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    locale: 'ko',
    setLocale: vi.fn(),
    t: (key: string) => key === 'language.label' ? '언어 선택' : key,
  }),
}));

let root: Root | null = null;
let container: HTMLDivElement | null = null;

afterEach(async () => {
  if (root) await act(async () => root?.unmount());
  container?.remove();
  root = null;
  container = null;
});

describe('LanguageSwitcher', () => {
  it('언어 선택기에 스크린 리더가 읽을 이름을 제공한다', async () => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);

    await act(async () => root?.render(<LanguageSwitcher />));

    const trigger = container.querySelector('[role="combobox"]');
    expect(trigger?.getAttribute('aria-label')).toBe('언어 선택');
  });
});
