'use client';

// I18nProvider — 전역 로케일 상태를 React Context로 관리
import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import { type Locale, getStoredLocale, storeLocale, translate, loadLocale } from './index';

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>('ko');

  const setLocale = useCallback(async (newLocale: Locale) => {
    await loadLocale(newLocale);
    setLocaleState(newLocale);
    storeLocale(newLocale);
  }, []);

  // Keep the first server/client render identical; apply stored locale after hydration.
  useEffect(() => {
    const stored = getStoredLocale();
    if (stored !== 'ko') {
      loadLocale(stored).then(() => setLocaleState(stored));
    }
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) =>
      translate(locale, key, params),
    [locale]
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

/** useTranslation 훅에서 사용하는 내부 컨텍스트 접근자 */
export function useI18nContext(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error('useTranslation은 I18nProvider 내부에서만 사용 가능합니다');
  }
  return ctx;
}
