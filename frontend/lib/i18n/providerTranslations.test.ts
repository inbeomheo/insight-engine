import { describe, expect, it } from 'vitest';
import ko from './ko.json';
import en from './en.json';
import ja from './ja.json';

const translations = { ko, en, ja } as const;

describe('다중 AI 서비스 번역', () => {
  it.each(Object.entries(translations))('%s에 동적 서비스 수 문구가 있다', (_language, messages) => {
    expect(messages.onboarding.serviceCount).toContain('{count}');
    expect(messages.settings.multiServiceActive).toContain('{count}');
  });
});
