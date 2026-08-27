import { afterEach, describe, it, expect, beforeEach } from 'vitest';
import { useSettingsStore } from './settingsStore';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';
import { getStorageAccountNamespace, loadCustomStyles, loadWebhookUrl } from '@/lib/storage';
import type { CustomStyle } from '@/lib/types';

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

function customStyle(id: string): CustomStyle {
  return { id, name: id, icon: '🧠', prompt: `${id} prompt`, createdAt: 1 };
}

describe('settingsStore — transcriptLanguage', () => {
  beforeEach(() => {
    setAuthSession(null);
    localStorage.clear();
    useSettingsStore.setState({
      transcriptLanguage: null,
      selectedModel: '',
      customStyles: [],
      webhookUrl: '',
    });
  });

  afterEach(() => {
    setAuthSession(null);
  });

  it('기본값은 null(자동)이다', () => {
    expect(useSettingsStore.getState().transcriptLanguage).toBeNull();
  });

  it('setTranscriptLanguage로 언어를 지정할 수 있다', () => {
    useSettingsStore.getState().setTranscriptLanguage('ja');
    expect(useSettingsStore.getState().transcriptLanguage).toBe('ja');
  });

  it('null로 되돌리면 자동 모드로 복귀한다', () => {
    useSettingsStore.getState().setTranscriptLanguage('en');
    useSettingsStore.getState().setTranscriptLanguage(null);
    expect(useSettingsStore.getState().transcriptLanguage).toBeNull();
  });

  it('계정 전환 시 커스텀 스타일·웹훅만 격리하고 공용 모델 선택은 유지한다', () => {
    const accountA = getStorageAccountNamespace('account-a');
    const accountB = getStorageAccountNamespace('account-b');

    useSettingsStore.setState({ selectedModel: 'shared-model' });
    setAuthSession(authSession('account-a'));
    useSettingsStore.getState().addCustomStyle(customStyle('style-a'));
    useSettingsStore.getState().setWebhookUrl('https://a.example/hook');

    setAuthSession(authSession('account-b'));
    expect(useSettingsStore.getState()).toMatchObject({
      selectedModel: 'shared-model',
      customStyles: [],
      webhookUrl: '',
    });
    useSettingsStore.getState().addCustomStyle(customStyle('style-b'));
    useSettingsStore.getState().setWebhookUrl('https://b.example/hook');

    setAuthSession(authSession('account-a'));
    expect(useSettingsStore.getState().customStyles.map(({ id }) => id)).toEqual(['style-a']);
    expect(useSettingsStore.getState().webhookUrl).toBe('https://a.example/hook');
    expect(loadCustomStyles(accountB).map(({ id }) => id)).toEqual(['style-b']);
    expect(loadWebhookUrl(accountB)).toBe('https://b.example/hook');
    expect(loadCustomStyles(accountA).map(({ id }) => id)).toEqual(['style-a']);
  });
});
