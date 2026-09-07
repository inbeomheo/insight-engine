import { STORAGE_KEYS } from './constants';
import { getAuthSession } from './auth-session';
import type { Report, CustomStyle } from './types';

/**
 * 로그인하지 않은 브라우저 데이터를 나타내는 안정적인 네임스페이스입니다.
 * 기존의 비스코프 키는 이 익명 영역의 정식 키로 계속 사용합니다.
 * 따라서 익명 데이터는 보존되지만 로그인 계정으로 자동 복사되지 않습니다.
 */
export const ANONYMOUS_STORAGE_NAMESPACE = 'anonymous';

export function getStorageAccountNamespace(
  userId: string | null | undefined = getAuthSession()?.user.id,
): string {
  return userId
    ? `user:${encodeURIComponent(userId)}`
    : ANONYMOUS_STORAGE_NAMESPACE;
}

export function getAccountStorageKey(
  key: string,
  namespace = getStorageAccountNamespace(),
): string {
  // 기존 브라우저 데이터를 삭제·이동하지 않고 익명 영역으로 계속 사용한다.
  if (namespace === ANONYMOUS_STORAGE_NAMESPACE) return key;
  return `${key}:account:${namespace}`;
}

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

/** 현재 인증 계정에 바인딩된 localStorage load/save 쌍 */
export function makeAccountStorage<T>(key: string, fallback: T) {
  return {
    load: (namespace = getStorageAccountNamespace()): T =>
      safeGet<T>(getAccountStorageKey(key, namespace), fallback),
    save: (value: T, namespace = getStorageAccountNamespace()): boolean =>
      safeSet(getAccountStorageKey(key, namespace), value),
    loadIdle: (
      cb: (value: T) => void,
      namespace = getStorageAccountNamespace(),
    ) => {
      const doLoad = () => cb(safeGet<T>(getAccountStorageKey(key, namespace), fallback));
      if (typeof requestIdleCallback !== 'undefined') {
        requestIdleCallback(doLoad);
      } else {
        setTimeout(doLoad, 0);
      }
    },
  };
}

// ── 기존 export 유지 (호출부 변경 없음) ──────────────────────

const reportsStorage = makeAccountStorage<Report[]>(STORAGE_KEYS.REPORTS, []);
export const loadReports = reportsStorage.load;
export const saveReports = reportsStorage.save;

const modelStorage = makeStorage<string>(STORAGE_KEYS.MODEL, '');
export const loadSelectedModel = modelStorage.load;
export const saveSelectedModel = (id: string) => modelStorage.save(id);

const customStylesStorage = makeAccountStorage<CustomStyle[]>(STORAGE_KEYS.CUSTOM_STYLES, []);
export const loadCustomStyles = customStylesStorage.load;
export const saveCustomStyles = (styles: CustomStyle[], namespace?: string) =>
  customStylesStorage.save(styles, namespace);

const webhookStorage = makeAccountStorage<string>(STORAGE_KEYS.WEBHOOK_URL, '');
export const loadWebhookUrl = webhookStorage.load;
export const saveWebhookUrl = (url: string, namespace?: string) =>
  webhookStorage.save(url, namespace);

const onboardingStorage = makeStorage<boolean>(STORAGE_KEYS.ONBOARDING_DONE, false);
export const isOnboardingDone = onboardingStorage.load;
export const setOnboardingDone = () => onboardingStorage.save(true);
