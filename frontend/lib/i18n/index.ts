// i18n 시스템 코어 — 외부 라이브러리 없이 React Context 기반 경량 구현
import koTranslations from './ko.json';

export type Locale = 'ko' | 'en' | 'ja';

export type TranslationDict = Record<string, unknown>;

// Phase 7: en/ja는 동적 import — 기본 로케일(ko)만 번들에 포함
const localeLoaders: Record<string, () => Promise<TranslationDict>> = {
  en: () => import('./en.json').then(m => m.default as TranslationDict),
  ja: () => import('./ja.json').then(m => m.default as TranslationDict),
};

const translations: Record<Locale, TranslationDict> = {
  ko: koTranslations as TranslationDict,
  en: {} as TranslationDict,
  ja: {} as TranslationDict,
};

/** 로케일 데이터를 동적으로 로드합니다 (ko 이외) */
export async function loadLocale(locale: Locale): Promise<void> {
  if (locale === 'ko') return;
  // 이미 로드됨
  if (Object.keys(translations[locale]).length > 0) return;
  const loader = localeLoaders[locale];
  if (loader) {
    translations[locale] = await loader();
  }
}

const LOCALE_STORAGE_KEY = 'insight-engine-locale';

/** localStorage에서 저장된 로케일 읽기 */
export function getStoredLocale(): Locale {
  if (typeof window === 'undefined') return 'ko';
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (stored === 'ko' || stored === 'en' || stored === 'ja') return stored;
  return 'ko';
}

/** 로케일을 localStorage에 저장 */
export function storeLocale(locale: Locale): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale);
  }
}

/**
 * 중첩 키를 순회하며 값을 반환합니다.
 * 예: getNestedValue(obj, 'sidebar.title') → obj.sidebar.title
 */
function getNestedValue(obj: TranslationDict, key: string): string | undefined {
  const parts = key.split('.');
  let current: unknown = obj;
  for (const part of parts) {
    if (current === null || typeof current !== 'object') return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === 'string' ? current : undefined;
}

/**
 * 지정된 로케일에서 번역 값을 조회합니다.
 * 찾지 못하면 한국어(ko)로 폴백합니다.
 * 변수 대체: {count}, {name} 등을 params 객체로 치환합니다.
 */
export function translate(
  locale: Locale,
  key: string,
  params?: Record<string, string | number>
): string {
  let value =
    getNestedValue(translations[locale], key) ??
    getNestedValue(translations['ko'], key) ??
    key;

  if (params) {
    for (const [k, v] of Object.entries(params)) {
      value = value.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
    }
  }

  return value;
}

export { translations };
