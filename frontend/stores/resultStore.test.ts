import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { toast } from 'sonner';
import { useResultStore } from './resultStore';
import { createReport } from '@/lib/report-factory';
import { loadReports } from '@/lib/storage';
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

describe('resultStore — localStorage 용량 초과 경고', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // debouncedSave 내부의 requestIdleCallback을 동기 실행으로 대체해 결정적으로 만든다.
    vi.stubGlobal('requestIdleCallback', (cb: IdleRequestCallback) => {
      cb({ didTimeout: false, timeRemaining: () => 0 } as IdleDeadline);
      return 0;
    });
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
});
