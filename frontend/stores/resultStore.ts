import { create } from 'zustand';
import type { Report } from '@/lib/types';
import { loadReports, saveReports } from '@/lib/storage';

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
    saveReports(next);
    set({ reports: next });
  },

  removeReport: (id) => {
    const next = get().reports.filter((r) => r.id !== id);
    saveReports(next);
    set({ reports: next });
  },

  clearReports: () => {
    saveReports([]);
    set({ reports: [] });
  },

  updateReport: (id, partial) => {
    const next = get().reports.map((r) =>
      r.id === id ? { ...r, ...partial } : r
    );
    saveReports(next);
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
    set({ reports: loadReports() });
  },
}));
