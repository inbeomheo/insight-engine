import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { toast } from 'sonner';
import { PIN_STORAGE_KEY, useResultStore } from './resultStore';
import { createReport } from '@/lib/report-factory';
import {
  getAccountStorageKey,
  getStorageAccountNamespace,
  loadReports,
  saveReports,
} from '@/lib/storage';
import { STORAGE_KEYS } from '@/lib/constants';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';
import type { Report } from '@/lib/types';

// resultStore가 import 시점에 toast를 바인딩하므로 모듈 전체를 모킹한다.
vi.mock('sonner', () => ({
  toast: {
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    message: vi.fn(),
  },
}));

const STORAGE_FULL_WARNING = '저장 공간이 부족합니다. 오래된 결과를 삭제해주세요.';

function makeReport(overrides: Partial<Report> = {}): Report {
  return createReport({
    id: 'r1',
    url: 'https://youtu.be/abc',
    title: '테스트 제목',
    content: '본문',
    html: '<p>본문</p>',
    style: 'summary',
    ...overrides,
  });
}

function authSession(userId: string, token = `${userId}-token`): AuthSession {
  return {
    user: { id: userId, email: `${userId}@example.com` },
    session: { access_token: token },
  };
}

/**
 * 전역 localStorage를 교체해 setItem이 QuotaExceededError를 던지게 한다.
 * storage.ts는 bare `localStorage`(전역)를 참조하므로, 특정 인스턴스 spyOn이 아니라
 * 전역 바인딩 자체를 stubGlobal로 바꿔야 가로채진다. afterEach의 unstubAllGlobals로 복원.
 */
function makeStorageFull() {
  const real = window.localStorage;
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => real.getItem(k),
    setItem: () => {
      throw new DOMException('Quota exceeded', 'QuotaExceededError');
    },
    removeItem: (k: string) => real.removeItem(k),
    clear: () => real.clear(),
    key: (i: number) => real.key(i),
    get length() {
      return real.length;
    },
  });
}

function failNextStorageWrite() {
  const real = window.localStorage;
  let shouldFail = true;
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => real.getItem(k),
    setItem: (k: string, value: string) => {
      if (shouldFail) {
        shouldFail = false;
        throw new DOMException('Transient write failure', 'QuotaExceededError');
      }
      real.setItem(k, value);
    },
    removeItem: (k: string) => real.removeItem(k),
    clear: () => real.clear(),
    key: (i: number) => real.key(i),
    get length() {
      return real.length;
    },
  });
}

describe('resultStore — localStorage 용량 초과 경고', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // debouncedSave 내부의 requestIdleCallback을 동기 실행으로 대체해 결정적으로 만든다.
    vi.stubGlobal('requestIdleCallback', (cb: IdleRequestCallback) => {
      cb({ didTimeout: false, timeRemaining: () => 0 } as IdleDeadline);
      return 0;
    });
    setAuthSession(null);
    window.localStorage.clear();
    useResultStore.setState({
      reports: [],
      searchQuery: '',
      styleFilter: '',
      pinnedIds: new Set<string>(),
    });
    vi.mocked(toast.warning).mockClear();
  });

  afterEach(() => {
    setAuthSession(null);
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('정상 저장 시 경고가 뜨지 않고 localStorage에 기록된다', () => {
    useResultStore.getState().addReport(makeReport());

    // 저장은 디바운스(500ms) + idle 시점이라 즉시 실행되지 않는다
    expect(loadReports()).toHaveLength(0);

    vi.advanceTimersByTime(500);

    expect(vi.mocked(toast.warning)).not.toHaveBeenCalled();
    expect(loadReports()).toHaveLength(1);
    expect(loadReports()[0].id).toBe('r1');
  });

  it('addReport는 스트리밍 표시가 없는 새 보고서를 false로 정규화한다', () => {
    useResultStore.getState().addReport(makeReport());

    expect(useResultStore.getState().reports[0].is_streaming).toBe(false);
  });

  it('hydrate는 필드가 없는 기존 보고서와 종료된 임시 스냅샷을 false로 복원한다', () => {
    const legacyReport = makeReport({ id: 'legacy' });
    delete legacyReport.is_streaming;
    const staleStreamingReport = makeReport({ id: 'stale-stream', is_streaming: true });
    localStorage.setItem(
      STORAGE_KEYS.REPORTS,
      JSON.stringify([legacyReport, staleStreamingReport]),
    );

    useResultStore.getState().hydrate();

    expect(useResultStore.getState().reports).toEqual([
      expect.objectContaining({ id: 'legacy', is_streaming: false }),
      expect.objectContaining({ id: 'stale-stream', is_streaming: false }),
    ]);
  });

  it('addReport: 용량 초과 시 toast.warning이 비동기로 호출된다', () => {
    makeStorageFull();

    useResultStore.getState().addReport(makeReport());

    // 디바운스 타이머가 발화하기 전에는 경고가 없어야 한다 (비동기 전파 검증)
    expect(vi.mocked(toast.warning)).not.toHaveBeenCalled();

    vi.advanceTimersByTime(500);

    expect(vi.mocked(toast.warning)).toHaveBeenCalledTimes(1);
    expect(vi.mocked(toast.warning)).toHaveBeenCalledWith(STORAGE_FULL_WARNING);
    // 저장 실패와 무관하게 인메모리 상태는 갱신된다
    expect(useResultStore.getState().reports).toHaveLength(1);
  });

  it('removeReport: 대기 중인 addReport 저장을 취소해 삭제 상태를 유지한다', () => {
    useResultStore.getState().addReport(makeReport());
    useResultStore.getState().removeReport('r1');

    vi.advanceTimersByTime(500);

    expect(useResultStore.getState().reports).toHaveLength(0);
    expect(loadReports()).toHaveLength(0);
  });

  it('updateReport: 용량 초과 시 toast.warning이 호출된다', () => {
    // 먼저 정상 저장으로 리포트 1건을 만든다
    useResultStore.getState().addReport(makeReport());
    vi.advanceTimersByTime(500);
    vi.mocked(toast.warning).mockClear();

    // 이후 저장부터 용량 초과 발생
    makeStorageFull();
    useResultStore.getState().updateReport('r1', { title: '수정된 제목' });

    expect(vi.mocked(toast.warning)).not.toHaveBeenCalled();
    vi.advanceTimersByTime(500);

    expect(vi.mocked(toast.warning)).toHaveBeenCalledWith(STORAGE_FULL_WARNING);
  });

  it('updateReport: 실제 변경이 없으면 저장도 경고도 발생하지 않는다', () => {
    useResultStore.getState().addReport(makeReport({ title: '동일' }));
    vi.advanceTimersByTime(500);
    vi.mocked(toast.warning).mockClear();

    makeStorageFull();
    // 같은 값으로 업데이트 → hasChange === false → 저장 스킵
    useResultStore.getState().updateReport('r1', { title: '동일' });
    vi.advanceTimersByTime(500);

    expect(vi.mocked(toast.warning)).not.toHaveBeenCalled();
  });

  it('updateReportPersisted: 반환 전에 localStorage 저장을 완료한다', () => {
    useResultStore.setState({ reports: [makeReport()] });

    const saved = useResultStore.getState().updateReportPersisted('r1', { title: '즉시 저장 제목' });

    expect(saved).toBe(true);
    expect(loadReports()[0].title).toBe('즉시 저장 제목');
    expect(useResultStore.getState().reports[0].title).toBe('즉시 저장 제목');
  });

  it('updateReportPersisted: 저장 실패 시 성공을 반환하거나 메모리 상태를 바꾸지 않는다', () => {
    useResultStore.setState({ reports: [makeReport()] });
    makeStorageFull();

    const saved = useResultStore.getState().updateReportPersisted('r1', { title: '유실될 제목' });

    expect(saved).toBe(false);
    expect(useResultStore.getState().reports[0].title).toBe('테스트 제목');
  });

  it('updateReportPersisted: idle 큐의 구형 저장이 즉시 저장을 덮어쓰지 못한다', () => {
    let idleSave: IdleRequestCallback | undefined;
    vi.stubGlobal('requestIdleCallback', (cb: IdleRequestCallback) => {
      idleSave = cb;
      return 1;
    });
    useResultStore.getState().addReport(makeReport({ title: '구형 제목' }));
    vi.advanceTimersByTime(500);

    const saved = useResultStore.getState().updateReportPersisted('r1', { title: '최종 제목' });
    idleSave?.({ didTimeout: false, timeRemaining: () => 0 } as IdleDeadline);

    expect(saved).toBe(true);
    expect(loadReports()[0].title).toBe('최종 제목');
  });

  it('updateReportPersisted: 즉시 저장 실패 시 기존 대기 스냅샷을 다시 저장한다', () => {
    const original = makeReport({ content: '원본 본문' });
    useResultStore.setState({ reports: [original] });
    localStorage.setItem(STORAGE_KEYS.REPORTS, JSON.stringify([original]));

    useResultStore.getState().updateReport('r1', { content: '먼저 대기 중인 본문' });
    failNextStorageWrite();

    const saved = useResultStore.getState().updateReportPersisted('r1', { title: '실패할 즉시 제목' });
    expect(saved).toBe(false);
    expect(useResultStore.getState().reports[0]).toMatchObject({
      title: '테스트 제목',
      content: '먼저 대기 중인 본문',
    });

    vi.advanceTimersByTime(500);

    expect(loadReports()[0]).toMatchObject({
      title: '테스트 제목',
      content: '먼저 대기 중인 본문',
    });
  });

  it('updateReportPersisted: idle 큐로 넘어간 대기 스냅샷도 실패 후 복구한다', () => {
    const idleCallbacks: IdleRequestCallback[] = [];
    vi.stubGlobal('requestIdleCallback', (cb: IdleRequestCallback) => {
      idleCallbacks.push(cb);
      return idleCallbacks.length;
    });
    const deadline = { didTimeout: false, timeRemaining: () => 0 } as IdleDeadline;
    const original = makeReport({ content: '원본 본문' });
    useResultStore.setState({ reports: [original] });
    localStorage.setItem(STORAGE_KEYS.REPORTS, JSON.stringify([original]));

    useResultStore.getState().updateReport('r1', { content: 'idle 대기 본문' });
    vi.advanceTimersByTime(500);
    expect(idleCallbacks).toHaveLength(1);

    failNextStorageWrite();
    expect(useResultStore.getState().updateReportPersisted('r1', { title: '실패할 제목' })).toBe(false);

    // 취소된 구형 idle 콜백은 저장하지 않고, 복구 예약된 새 콜백만 최신 대기 스냅샷을 쓴다.
    idleCallbacks[0](deadline);
    vi.advanceTimersByTime(500);
    expect(idleCallbacks).toHaveLength(2);
    idleCallbacks[1](deadline);

    expect(loadReports()[0]).toMatchObject({
      title: '테스트 제목',
      content: 'idle 대기 본문',
    });
  });

  it('A → 로그아웃 → B 전환 시 보고서·핀을 즉시 격리하고 각 계정 데이터를 보존한다', () => {
    const accountA = getStorageAccountNamespace('account-a');
    const accountB = getStorageAccountNamespace('account-b');

    setAuthSession(authSession('account-a'));
    useResultStore.getState().addReport(makeReport({ id: 'report-a', title: 'A 보고서' }));
    useResultStore.getState().togglePin('report-a');

    // 디바운스 저장 전에 로그아웃해도 A 스냅샷은 A 키에 마무리된다.
    setAuthSession(null);
    expect(useResultStore.getState().reports).toEqual([]);
    expect([...useResultStore.getState().pinnedIds]).toEqual([]);
    expect(loadReports(accountA).map(({ id }) => id)).toEqual(['report-a']);

    setAuthSession(authSession('account-b'));
    expect(useResultStore.getState().reports).toEqual([]);
    expect([...useResultStore.getState().pinnedIds]).toEqual([]);
    useResultStore.getState().addReport(makeReport({ id: 'report-b', title: 'B 보고서' }));
    useResultStore.getState().togglePin('report-b');

    setAuthSession(authSession('account-a', 'account-a-refreshed'));
    expect(useResultStore.getState().reports.map(({ id }) => id)).toEqual(['report-a']);
    expect([...useResultStore.getState().pinnedIds]).toEqual(['report-a']);
    expect(loadReports(accountB).map(({ id }) => id)).toEqual(['report-b']);
    expect(
      localStorage.getItem(getAccountStorageKey(PIN_STORAGE_KEY, accountB)),
    ).toContain('report-b');
    expect(localStorage.getItem(STORAGE_KEYS.REPORTS)).toBeNull();
  });

  it('같은 사용자의 토큰 갱신은 상태나 대기 저장을 초기화하지 않는다', () => {
    setAuthSession(authSession('account-a', 'old-token'));
    useResultStore.getState().addReport(makeReport({ id: 'same-user' }));

    setAuthSession(authSession('account-a', 'new-token'));

    expect(useResultStore.getState().reports.map(({ id }) => id)).toEqual(['same-user']);
    vi.advanceTimersByTime(500);
    expect(loadReports().map(({ id }) => id)).toEqual(['same-user']);
  });

  it('A의 늦은 hydrate 콜백이 B 메모리를 덮지 못한다', () => {
    const callbacks: IdleRequestCallback[] = [];
    vi.stubGlobal('requestIdleCallback', (callback: IdleRequestCallback) => {
      callbacks.push(callback);
      return callbacks.length;
    });
    const deadline = { didTimeout: false, timeRemaining: () => 0 } as IdleDeadline;
    const accountA = getStorageAccountNamespace('account-a');
    const accountB = getStorageAccountNamespace('account-b');
    saveReports([makeReport({ id: 'report-a' })], accountA);
    saveReports([makeReport({ id: 'report-b' })], accountB);

    setAuthSession(authSession('account-a'));
    setAuthSession(authSession('account-b'));
    expect(callbacks).toHaveLength(2);

    callbacks[0](deadline);
    expect(useResultStore.getState().reports).toEqual([]);
    callbacks[1](deadline);
    expect(useResultStore.getState().reports.map(({ id }) => id)).toEqual(['report-b']);
  });
});
