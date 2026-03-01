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

// 보고서 히스토리
export function loadReports(): Report[] {
  return safeGet<Report[]>(STORAGE_KEYS.REPORTS, []);
}

export function saveReports(reports: Report[]): boolean {
  return safeSet(STORAGE_KEYS.REPORTS, reports);
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

// Ollama Base URL
export function loadOllamaBaseUrl(): string {
  return safeGet<string>(STORAGE_KEYS.OLLAMA_BASE_URL, '');
}

export function saveOllamaBaseUrl(url: string) {
  safeSet(STORAGE_KEYS.OLLAMA_BASE_URL, url);
}

// 웹훅 URL
export function loadWebhookUrl(): string {
  return safeGet<string>(STORAGE_KEYS.WEBHOOK_URL, '');
}

export function saveWebhookUrl(url: string) {
  safeSet(STORAGE_KEYS.WEBHOOK_URL, url);
}

// 온보딩
export function isOnboardingDone(): boolean {
  return safeGet<boolean>(STORAGE_KEYS.ONBOARDING_DONE, false);
}

export function setOnboardingDone() {
  safeSet(STORAGE_KEYS.ONBOARDING_DONE, true);
}
