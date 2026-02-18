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

function safeSet(key: string, value: unknown) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage full 등 무시
  }
}

// 보고서 히스토리
export function loadReports(): Report[] {
  return safeGet<Report[]>(STORAGE_KEYS.REPORTS, []);
}

export function saveReports(reports: Report[]) {
  safeSet(STORAGE_KEYS.REPORTS, reports);
}

// 프로바이더/모델 선택
export function loadSelectedProvider(): string {
  return safeGet<string>(STORAGE_KEYS.PROVIDER, '');
}

export function saveSelectedProvider(id: string) {
  safeSet(STORAGE_KEYS.PROVIDER, id);
}

export function loadSelectedModel(): string {
  return safeGet<string>(STORAGE_KEYS.MODEL, '');
}

export function saveSelectedModel(id: string) {
  safeSet(STORAGE_KEYS.MODEL, id);
}

// 커스텀 스타일
export function loadCustomStyles(): CustomStyle[] {
  return safeGet<CustomStyle[]>(STORAGE_KEYS.CUSTOM_STYLES, []);
}

export function saveCustomStyles(styles: CustomStyle[]) {
  safeSet(STORAGE_KEYS.CUSTOM_STYLES, styles);
}

// 온보딩
export function isOnboardingDone(): boolean {
  return safeGet<boolean>(STORAGE_KEYS.ONBOARDING_DONE, false);
}

export function setOnboardingDone() {
  safeSet(STORAGE_KEYS.ONBOARDING_DONE, true);
}
