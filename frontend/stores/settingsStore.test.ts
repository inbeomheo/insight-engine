import { describe, it, expect, beforeEach } from 'vitest';
import { useSettingsStore } from './settingsStore';

describe('settingsStore — transcriptLanguage', () => {
  beforeEach(() => {
    useSettingsStore.setState({ transcriptLanguage: null });
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
});
