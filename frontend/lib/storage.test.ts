import { beforeEach, describe, expect, it } from 'vitest';
import { createReport } from './report-factory';
import {
  ANONYMOUS_STORAGE_NAMESPACE,
  getAccountStorageKey,
  getStorageAccountNamespace,
  loadReports,
  saveReports,
} from './storage';
import { STORAGE_KEYS } from './constants';

function report(id: string) {
  return createReport({
    id,
    url: '',
    title: id,
    content: `${id} 본문`,
    html: `<p>${id}</p>`,
    style: 'summary',
  });
}

describe('account-bound storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('기존 키를 안정적인 익명 영역으로 유지하고 계정 키만 분리한다', () => {
    const anonymous = getStorageAccountNamespace(null);
    const accountA = getStorageAccountNamespace('user/a');
    const accountB = getStorageAccountNamespace('user/b');

    expect(anonymous).toBe(ANONYMOUS_STORAGE_NAMESPACE);
    expect(getAccountStorageKey(STORAGE_KEYS.REPORTS, anonymous)).toBe(STORAGE_KEYS.REPORTS);
    expect(getAccountStorageKey(STORAGE_KEYS.REPORTS, accountA)).not.toBe(
      getAccountStorageKey(STORAGE_KEYS.REPORTS, accountB),
    );
  });

  it('익명·A·B 보고서를 서로 복사하지 않고 각자 보존한다', () => {
    const anonymous = getStorageAccountNamespace(null);
    const accountA = getStorageAccountNamespace('account-a');
    const accountB = getStorageAccountNamespace('account-b');

    expect(saveReports([report('anonymous')], anonymous)).toBe(true);
    expect(saveReports([report('a')], accountA)).toBe(true);
    expect(saveReports([report('b')], accountB)).toBe(true);

    expect(loadReports(anonymous).map(({ id }) => id)).toEqual(['anonymous']);
    expect(loadReports(accountA).map(({ id }) => id)).toEqual(['a']);
    expect(loadReports(accountB).map(({ id }) => id)).toEqual(['b']);
    expect(localStorage.getItem(STORAGE_KEYS.REPORTS)).toContain('anonymous');
  });
});
