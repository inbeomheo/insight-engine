import { create } from 'zustand';
import { toast } from 'sonner';
import type { Report } from '@/lib/types';
import { loadReports, saveReports } from '@/lib/storage';

// localStorage 저장을 디바운스 — 빠른 연속 호출 시 마지막 1회만 실제 write
let saveTimer: ReturnType<typeof setTimeout> | null = null;
function debouncedSave(reports: Report[]): boolean {
  if (saveTimer) clearTimeout(saveTimer);
  let result = true;
  saveTimer = setTimeout(() => {
    result = saveReports(reports);
  }, 300);
  return result;
}

interface ResultState {
  reports: Report[];
  searchQuery: string;
  styleFilter: string;

  addReport: (r: Report) => void;
  removeReport: (id: string) => void;
  clearReports: () => void;
  updateReport: (id: string, partial: Partial<Report>) => void;

  setSearchQuery: (q: string) => void;
  setStyleFilter: (s: string) => void;

  filteredReports: () => Report[];

  hydrate: () => void;
}

export const useResultStore = create<ResultState>((set, get) => ({
  reports: [],
  searchQuery: '',
  styleFilter: '',

  addReport: (r) => {
    const next = [r, ...get().reports];
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
    const next = get().reports.map((r) =>
      r.id === id ? { ...r, ...partial } : r
    );
    debouncedSave(next);
    set({ reports: next });
  },

  setSearchQuery: (q) => set({ searchQuery: q }),
  setStyleFilter: (s) => set({ styleFilter: s }),

  filteredReports: () => {
    const { reports, searchQuery, styleFilter } = get();
    return reports.filter((r) => {
      const matchStyle = !styleFilter || r.style === styleFilter;
      const matchSearch =
        !searchQuery ||
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.content.toLowerCase().includes(searchQuery.toLowerCase());
      return matchStyle && matchSearch;
    });
  },

  hydrate: () => {
    // Phase 4: 메인 스레드 블로킹 방지 — idle 시점에 JSON.parse 수행
    const load = () => set({ reports: loadReports() });
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(load);
    } else {
      setTimeout(load, 0);
    }
  },
}));
