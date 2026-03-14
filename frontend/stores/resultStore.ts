import { create } from 'zustand';
import { toast } from 'sonner';
import type { Report } from '@/lib/types';
import { loadReports, saveReports } from '@/lib/storage';

// localStorage 저장을 디바운스 + idle 시점 실행 — 메인 스레드 블로킹 방지
let saveTimer: ReturnType<typeof setTimeout> | null = null;
function debouncedSave(reports: Report[]): boolean {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    // idle 시점에 JSON.stringify 수행 (메인 스레드 블로킹 방지)
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(() => saveReports(reports), { timeout: 2000 });
    } else {
      saveReports(reports);
    }
  }, 500);
  return true;
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

  setSearchQuery: (q: string) => void;
  setStyleFilter: (s: string) => void;

  /** F8-25: 핀 고정/해제 토글 */
  togglePin: (id: string) => void;
  /** F8-25: 핀 고정된 리포트만 반환 */
  pinnedReports: () => Report[];

  filteredReports: () => Report[];

  hydrate: () => void;
}

const PIN_STORAGE_KEY = 'insight_engine_pinned_ids';

function loadPinnedIds(): Set<string> {
  try {
    const raw = localStorage.getItem(PIN_STORAGE_KEY);
    if (!raw) return new Set();
    return new Set(JSON.parse(raw) as string[]);
  } catch {
    return new Set();
  }
}

function savePinnedIds(ids: Set<string>): void {
  try {
    localStorage.setItem(PIN_STORAGE_KEY, JSON.stringify([...ids]));
  } catch {
    // 저장 실패는 무시
  }
}

export const useResultStore = create<ResultState>((set, get) => ({
  reports: [],
  searchQuery: '',
  styleFilter: '',
  pinnedIds: new Set<string>(),

  addReport: (r) => {
    const MAX_REPORTS = 20;
    let next = [r, ...get().reports];
    if (next.length > MAX_REPORTS) {
      next = next.slice(0, MAX_REPORTS);
    }
    if (!debouncedSave(next)) {
      toast.warning('저장 공간이 부족합니다. 오래된 결과를 삭제해주세요.');
    }
    set({ reports: next });
  },

  removeReport: (id) => {
    const next = get().reports.filter((r) => r.id !== id);
    saveReports(next); // 삭제는 즉시 저장
    set({ reports: next });
  },

  clearReports: () => {
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
    debouncedSave(next);
    set({ reports: next });
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
    // Phase 4: 메인 스레드 블로킹 방지 — idle 시점에 JSON.parse 수행
    const load = () => set({ reports: loadReports(), pinnedIds: loadPinnedIds() });
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(load);
    } else {
      setTimeout(load, 0);
    }
  },
}));
