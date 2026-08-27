import { create } from 'zustand';
import { toast } from 'sonner';
import type { Report } from '@/lib/types';
import {
  getStorageAccountNamespace,
  loadReports,
  makeAccountStorage,
  saveReports,
} from '@/lib/storage';
import { subscribeAuthSession } from '@/lib/auth-session';

const STORAGE_FULL_WARNING = '저장 공간이 부족합니다. 오래된 결과를 삭제해주세요.';
export const MAX_LOCAL_REPORTS = 20;
const warnStorageFull = () => toast.warning(STORAGE_FULL_WARNING);

// localStorage 저장을 디바운스 + idle 시점 실행 — 메인 스레드 블로킹 방지.
// 저장은 비동기로 예약되므로 결과를 동기 반환할 수 없다. 실패(QuotaExceededError 등으로
// saveReports가 false 반환)는 onError 콜백으로 비동기 전파한다.
let saveRevision = 0;
interface PendingSave {
  reports: Report[];
  onError?: () => void;
  namespace: string;
  revision: number;
  timer: ReturnType<typeof setTimeout> | null;
}
let pendingSave: PendingSave | null = null;
let activeStorageNamespace = getStorageAccountNamespace();
let hydrationRevision = 0;

function cancelPendingSave(): PendingSave | null {
  // 타이머가 이미 발화해 requestIdleCallback 큐로 넘어간 저장도 무효화한다.
  saveRevision += 1;
  const cancelled = pendingSave;
  if (cancelled && cancelled.timer !== null) {
    clearTimeout(cancelled.timer);
    cancelled.timer = null;
  }
  pendingSave = null;
  return cancelled;
}

function debouncedSave(
  reports: Report[],
  onError?: () => void,
  namespace = getStorageAccountNamespace(),
): void {
  cancelPendingSave();
  const scheduled: PendingSave = {
    reports,
    onError,
    namespace,
    revision: saveRevision,
    timer: null,
  };
  pendingSave = scheduled;
  scheduled.timer = setTimeout(() => {
    if (scheduled.revision !== saveRevision || pendingSave !== scheduled) return;
    scheduled.timer = null;
    // idle 시점에 JSON.stringify 수행 (메인 스레드 블로킹 방지)
    const run = () => {
      if (scheduled.revision !== saveRevision || pendingSave !== scheduled) return;
      pendingSave = null;
      if (!saveReports(reports, namespace)) onError?.();
    };
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(run, { timeout: 2000 });
    } else {
      run();
    }
  }, 500);
}

interface ResultState {
  reports: Report[];
  searchQuery: string;
  styleFilter: string;
  /** F8-25: 고정된 리포트 ID 집합 */
  pinnedIds: Set<string>;

  addReport: (r: Report) => void;
  removeReport: (id: string) => void;
  clearReports: () => void;
  updateReport: (id: string, partial: Partial<Report>) => void;
  /** 편집 저장처럼 영속화 완료를 확인해야 하는 업데이트. 성공할 때만 상태도 갱신한다. */
  updateReportPersisted: (id: string, partial: Partial<Report>) => boolean;

  setSearchQuery: (q: string) => void;
  setStyleFilter: (s: string) => void;

  /** F8-25: 핀 고정/해제 토글 */
  togglePin: (id: string) => void;
  /** F8-25: 핀 고정된 리포트만 반환 */
  pinnedReports: () => Report[];

  filteredReports: () => Report[];

  hydrate: () => void;
}

export const PIN_STORAGE_KEY = 'insight_engine_pinned_ids';
const pinnedIdsStorage = makeAccountStorage<string[]>(PIN_STORAGE_KEY, []);

function loadPinnedIds(namespace = getStorageAccountNamespace()): Set<string> {
  try {
    return new Set(pinnedIdsStorage.load(namespace));
  } catch {
    return new Set();
  }
}

function savePinnedIds(
  ids: Set<string>,
  namespace = getStorageAccountNamespace(),
): void {
  pinnedIdsStorage.save([...ids], namespace);
}

function normalizeAddedReport(report: Report): Report {
  return { ...report, is_streaming: report.is_streaming === true };
}

function normalizeHydratedReports(reports: Report[]): Report[] {
  // 새로고침 후에는 해당 보고서를 갱신할 실행 중 스트림이 없다.
  // 이전 세션의 임시 스냅샷과 필드가 없는 기존 보고서를 모두 편집 가능한 상태로 복원한다.
  return reports.map((report) => ({ ...report, is_streaming: false }));
}

export const useResultStore = create<ResultState>((set, get) => ({
  reports: [],
  searchQuery: '',
  styleFilter: '',
  pinnedIds: new Set<string>(),

  addReport: (r) => {
    let next = [normalizeAddedReport(r), ...get().reports];
    if (next.length > MAX_LOCAL_REPORTS) {
      next = next.slice(0, MAX_LOCAL_REPORTS);
    }
    debouncedSave(next, warnStorageFull);
    set({ reports: next });
  },

  removeReport: (id) => {
    const next = get().reports.filter((r) => r.id !== id);
    cancelPendingSave();
    saveReports(next); // 삭제는 즉시 저장
    set({ reports: next });
  },

  clearReports: () => {
    cancelPendingSave();
    saveReports([]); // 전체 삭제도 즉시 저장
    set({ reports: [] });
  },

  updateReport: (id, partial) => {
    const reports = get().reports;
    const idx = reports.findIndex((r) => r.id === id);
    if (idx === -1) return;
    // 동일 참조 방지: 실제 변경이 있을 때만 업데이트
    const target = reports[idx];
    const keys = Object.keys(partial) as (keyof Report)[];
    const hasChange = keys.some((k) => target[k] !== partial[k]);
    if (!hasChange) return;
    const next = [...reports];
    next[idx] = { ...target, ...partial };
    debouncedSave(next, warnStorageFull);
    set({ reports: next });
  },

  updateReportPersisted: (id, partial) => {
    const reports = get().reports;
    const idx = reports.findIndex((r) => r.id === id);
    if (idx === -1) return false;
    const target = reports[idx];
    const keys = Object.keys(partial) as (keyof Report)[];
    const hasChange = keys.some((k) => target[k] !== partial[k]);
    if (!hasChange) return true;

    const next = [...reports];
    next[idx] = { ...target, ...partial };
    // 예약된 구형 스냅샷이 이 즉시 저장 뒤에 실행되어 덮어쓰지 못하게 먼저 무효화한다.
    const cancelledSave = cancelPendingSave();
    if (!saveReports(next)) {
      // 즉시 저장이 실패해도 그 전에 대기하던 변경까지 유실하면 안 된다.
      // 타이머 단계와 idle 큐 단계 모두 PendingSave에 스냅샷을 보관하므로 안전하게 재예약할 수 있다.
      if (cancelledSave) {
        debouncedSave(
          cancelledSave.reports,
          cancelledSave.onError,
          cancelledSave.namespace,
        );
      }
      return false;
    }
    set({ reports: next });
    return true;
  },

  setSearchQuery: (q) => set({ searchQuery: q }),
  setStyleFilter: (s) => set({ styleFilter: s }),

  // F8-25: 핀 고정/해제 토글
  togglePin: (id) => {
    const next = new Set(get().pinnedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    savePinnedIds(next);
    set({ pinnedIds: next });
  },

  // F8-25: 고정된 리포트만 반환 (핀 순서 유지)
  pinnedReports: () => {
    const { reports, pinnedIds } = get();
    return reports.filter((r) => pinnedIds.has(r.id));
  },

  filteredReports: () => {
    const { reports, searchQuery, styleFilter } = get();
    if (!searchQuery && !styleFilter) return reports;
    const lowerQuery = searchQuery?.toLowerCase();
    return reports.filter((r) => {
      if (styleFilter && r.style !== styleFilter) return false;
      if (!lowerQuery) return true;
      return (
        r.title.toLowerCase().includes(lowerQuery) ||
        r.content.toLowerCase().includes(lowerQuery)
      );
    });
  },

  hydrate: () => {
    const namespace = getStorageAccountNamespace();
    const revision = ++hydrationRevision;
    // Phase 4: 메인 스레드 블로킹 방지 — idle 시점에 JSON.parse 수행
    const load = () => {
      if (
        revision !== hydrationRevision
        || namespace !== activeStorageNamespace
        || namespace !== getStorageAccountNamespace()
      ) return;
      set({
        reports: normalizeHydratedReports(loadReports(namespace)),
        pinnedIds: loadPinnedIds(namespace),
      });
    };
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(load);
    } else {
      setTimeout(load, 0);
    }
  },
}));

// 세션 토큰 갱신은 같은 계정이므로 상태를 유지하고, 사용자 ID가 바뀌 때만
// 예약 저장을 기존 계정 키에 마무리한 뒤 메모리를 비우고 새 계정을 로드한다.
subscribeAuthSession(() => {
  const nextNamespace = getStorageAccountNamespace();
  if (nextNamespace === activeStorageNamespace) return;

  const cancelledSave = cancelPendingSave();
  if (
    cancelledSave
    && !saveReports(cancelledSave.reports, cancelledSave.namespace)
  ) {
    cancelledSave.onError?.();
  }

  activeStorageNamespace = nextNamespace;
  hydrationRevision += 1;
  useResultStore.setState({
    reports: [],
    searchQuery: '',
    styleFilter: '',
    pinnedIds: new Set<string>(),
  });
  useResultStore.getState().hydrate();
});
