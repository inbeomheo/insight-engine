import { STORAGE_KEYS } from './constants';
import type { Report, CustomStyle } from './types';

function safeGet<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function safeSet(key: string, value: unknown): boolean {
  if (typeof window === 'undefined') return false;
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

/** localStorage 키에 대한 load/save 쌍을 생성하는 팩토리 */
export function makeStorage<T>(key: string, fallback: T) {
  return {
    load: (): T => safeGet<T>(key, fallback),
    save: (value: T): boolean => safeSet(key, value),
    /** requestIdleCallback 기반 비동기 로드 (hydrate용) */
    loadIdle: (cb: (value: T) => void) => {
      const doLoad = () => cb(safeGet<T>(key, fallback));
      if (typeof requestIdleCallback !== 'undefined') {
        requestIdleCallback(doLoad);
      } else {
        setTimeout(doLoad, 0);
      }
    },
  };
}

// ── 기존 export 유지 (호출부 변경 없음) ──────────────────────

const reportsStorage = makeStorage<Report[]>(STORAGE_KEYS.REPORTS, []);
export const loadReports = reportsStorage.load;
export const saveReports = reportsStorage.save;

const providerStorage = makeStorage<string>(STORAGE_KEYS.PROVIDER, '');
export const loadSelectedProvider = providerStorage.load;
export const saveSelectedProvider = (id: string) => providerStorage.save(id);

const modelStorage = makeStorage<string>(STORAGE_KEYS.MODEL, '');
export const loadSelectedModel = modelStorage.load;
export const saveSelectedModel = (id: string) => modelStorage.save(id);

const customStylesStorage = makeStorage<CustomStyle[]>(STORAGE_KEYS.CUSTOM_STYLES, []);
export const loadCustomStyles = customStylesStorage.load;
export const saveCustomStyles = (styles: CustomStyle[]) => customStylesStorage.save(styles);

const webhookStorage = makeStorage<string>(STORAGE_KEYS.WEBHOOK_URL, '');
export const loadWebhookUrl = webhookStorage.load;
export const saveWebhookUrl = (url: string) => webhookStorage.save(url);

const onboardingStorage = makeStorage<boolean>(STORAGE_KEYS.ONBOARDING_DONE, false);
export const isOnboardingDone = onboardingStorage.load;
export const setOnboardingDone = () => onboardingStorage.save(true);
