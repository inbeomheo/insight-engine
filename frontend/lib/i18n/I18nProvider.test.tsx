import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it } from 'vitest';
import { useTranslation } from '@/hooks/useTranslation';
import { I18nProvider } from './I18nProvider';

let root: Root | null = null;
let container: HTMLDivElement | null = null;
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function TranslationProbe() {
  const { t } = useTranslation();
  return <span>{t('common.generate')}</span>;
}

describe('I18nProvider', () => {
  afterEach(() => {
    act(() => root?.unmount());
    container?.remove();
    root = null;
    container = null;
    localStorage.clear();
    document.documentElement.lang = 'ko';
  });

  it.each([
    ['en', 'Generate'],
    ['ja', '生成する'],
  ] as const)('저장된 %s 로케일의 동적 로드가 끝나면 번역을 다시 렌더한다', async (locale, expected) => {
    localStorage.setItem('insight-engine-locale', locale);

    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => {
      root!.render(
        <I18nProvider>
          <TranslationProbe />
        </I18nProvider>,
      );
    });
    for (let attempt = 0; attempt < 100 && container.textContent !== expected; attempt += 1) {
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 10));
      });
    }

    expect(container.textContent).toBe(expected);
    expect(document.documentElement.lang).toBe(locale);
  });
});
