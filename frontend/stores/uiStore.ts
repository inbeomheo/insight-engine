import { create } from 'zustand';

interface UIState {
  sidebarOpen: boolean;
  settingsPopoverOpen: boolean;
  settingsModalOpen: boolean;
  onboardingOpen: boolean;
  customStyleModalOpen: boolean;
  mindmapModalOpen: boolean;
  promptModalOpen: boolean;
  playlistModalOpen: boolean;

  // 현재 모달에 표시 중인 데이터
  activePrompt: string;
  activeMindmapReportId: string;
  editingCustomStyleId: string | null;

  toggleSidebar: () => void;
  setSidebarOpen: (v: boolean) => void;
  setSettingsPopoverOpen: (v: boolean) => void;
  setSettingsModalOpen: (v: boolean) => void;
  setOnboardingOpen: (v: boolean) => void;
  setCustomStyleModalOpen: (v: boolean, editId?: string | null) => void;
  setMindmapModalOpen: (v: boolean, reportId?: string) => void;
  setPromptModalOpen: (v: boolean, prompt?: string) => void;
  setPlaylistModalOpen: (v: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  settingsPopoverOpen: false,
  settingsModalOpen: false,
  onboardingOpen: false,
  customStyleModalOpen: false,
  mindmapModalOpen: false,
  promptModalOpen: false,
  playlistModalOpen: false,
  activePrompt: '',
  activeMindmapReportId: '',
  editingCustomStyleId: null,

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  setSettingsPopoverOpen: (v) => set({ settingsPopoverOpen: v }),
  setSettingsModalOpen: (v) => set({ settingsModalOpen: v }),
  setOnboardingOpen: (v) => set({ onboardingOpen: v }),
  setCustomStyleModalOpen: (v, editId = null) =>
    set({ customStyleModalOpen: v, editingCustomStyleId: editId }),
  setMindmapModalOpen: (v, reportId = '') =>
    set({ mindmapModalOpen: v, activeMindmapReportId: reportId }),
  setPromptModalOpen: (v, prompt = '') =>
    set({ promptModalOpen: v, activePrompt: prompt }),
  setPlaylistModalOpen: (v) => set({ playlistModalOpen: v }),
}));
