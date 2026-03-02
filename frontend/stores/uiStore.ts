import { create } from 'zustand';

type ActiveView = 'main' | 'calendar';

/** 동시에 하나만 열리는 모달 종류 */
type ModalType =
  | 'settings'
  | 'onboarding'
  | 'customStyle'
  | 'mindmap'
  | 'prompt'
  | 'playlist'
  | 'workspaceSettings'
  | 'templateGallery'
  | null;

interface UIState {
  sidebarOpen: boolean;
  settingsPopoverOpen: boolean;

  /** 현재 열린 모달 (동시에 1개만) */
  activeModal: ModalType;

  // 모달에 연결된 데이터
  activePrompt: string;
  activeMindmapReportId: string;
  editingCustomStyleId: string | null;

  // 메인 뷰 전환
  activeView: ActiveView;
  setActiveView: (v: ActiveView) => void;

  // 사이드바 히스토리에서 선택된 리포트
  activeReportId: string | null;
  setActiveReportId: (id: string | null) => void;

  toggleSidebar: () => void;
  setSidebarOpen: (v: boolean) => void;
  setSettingsPopoverOpen: (v: boolean) => void;
  setSettingsModalOpen: (v: boolean) => void;
  setOnboardingOpen: (v: boolean) => void;
  setCustomStyleModalOpen: (v: boolean, editId?: string | null) => void;
  setMindmapModalOpen: (v: boolean, reportId?: string) => void;
  setPromptModalOpen: (v: boolean, prompt?: string) => void;
  setPlaylistModalOpen: (v: boolean) => void;
  setWorkspaceSettingsOpen: (v: boolean) => void;
  setTemplateGalleryOpen: (v: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  settingsPopoverOpen: false,
  activeModal: null,
  activeView: 'main',
  activePrompt: '',
  activeMindmapReportId: '',
  editingCustomStyleId: null,
  activeReportId: null,

  setActiveView: (v) => set({ activeView: v }),
  setActiveReportId: (id) => set({ activeReportId: id }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  setSettingsPopoverOpen: (v) => set({ settingsPopoverOpen: v }),

  setSettingsModalOpen: (v) =>
    set({ activeModal: v ? 'settings' : null }),
  setOnboardingOpen: (v) =>
    set({ activeModal: v ? 'onboarding' : null }),
  setCustomStyleModalOpen: (v, editId = null) =>
    set({ activeModal: v ? 'customStyle' : null, editingCustomStyleId: editId }),
  setMindmapModalOpen: (v, reportId = '') =>
    set({ activeModal: v ? 'mindmap' : null, activeMindmapReportId: reportId }),
  setPromptModalOpen: (v, prompt = '') =>
    set({ activeModal: v ? 'prompt' : null, activePrompt: prompt }),
  setPlaylistModalOpen: (v) =>
    set({ activeModal: v ? 'playlist' : null }),
  setWorkspaceSettingsOpen: (v) =>
    set({ activeModal: v ? 'workspaceSettings' : null }),
  setTemplateGalleryOpen: (v) =>
    set({ activeModal: v ? 'templateGallery' : null }),
}));
