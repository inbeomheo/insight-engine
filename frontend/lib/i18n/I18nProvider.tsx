'use client';

// I18nProvider — 전역 로케일 상태를 React Context로 관리
import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from 'react';
import {
  type Locale,
  type TranslationDict,
  getStoredLocale,
  storeLocale,
  translateWithMessages,
  loadLocale,
  translations,
} from './index';

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => getStoredLocale());
  const [messages, setMessages] = useState<TranslationDict>(() => translations[locale]);
  const localeRequestRef = useRef(0);

  const setLocale = useCallback(async (newLocale: Locale) => {
    const requestId = ++localeRequestRef.current;
    const loadedMessages = await loadLocale(newLocale);
    if (requestId !== localeRequestRef.current) return;
    setMessages(loadedMessages);
    setLocaleState(newLocale);
    storeLocale(newLocale);
  }, []);

  // 저장된 초기 로케일을 동적으로 로드하고, 언마운트/전환 후의 늦은 응답은 무시한다.
  useEffect(() => {
    const requestId = ++localeRequestRef.current;
    void loadLocale(locale).then((loadedMessages) => {
      if (requestId === localeRequestRef.current) setMessages(loadedMessages);
    });
    return () => {
      if (requestId === localeRequestRef.current) localeRequestRef.current += 1;
    };
  }, [locale]);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>) =>
      translateWithMessages(locale, key, messages, params),
    [locale, messages]
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
