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
  const [locale, setLocaleState] = useState<Locale>(() => getStoredLocale());

  const setLocale = useCallback(async (newLocale: Locale) => {
    await loadLocale(newLocale);
    setLocaleState(newLocale);
    storeLocale(newLocale);
  }, []);

  // 초기 로케일이 ko가 아닌 경우 동적 로드
  useEffect(() => {
    if (locale !== 'ko') loadLocale(locale).then(() => setLocaleState(l => l));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
