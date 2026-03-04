import { STYLE_OPTIONS } from './constants';

export function getStyleLabel(styleId: string): string {
  return STYLE_OPTIONS.find((s) => s.id === styleId)?.label || styleId;
}

export function getStyleEmoji(styleId: string): string {
  return STYLE_OPTIONS.find((s) => s.id === styleId)?.emoji || '📄';
}

export function formatTime(): string {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
}
