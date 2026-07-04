import { create } from 'zustand';

/** 위젯 정의 */
export interface DashboardWidget {
  id: string;
  type: string;
  title: string;
  x: number;   // 그리드 열 (0-based)
  y: number;   // 그리드 행 (0-based)
  w: number;   // 너비 (그리드 단위)
  h: number;   // 높이 (그리드 단위)
  visible: boolean;
}

/** 기본 위젯 레이아웃 */
const DEFAULT_WIDGETS: DashboardWidget[] = [
  { id: 'recent', type: 'recent_content', title: '최근 생성', x: 0, y: 0, w: 2, h: 1, visible: true },
  { id: 'stats', type: 'usage_stats', title: '사용 통계', x: 2, y: 0, w: 1, h: 1, visible: true },
  { id: 'quick', type: 'quick_actions', title: '빠른 작업', x: 0, y: 1, w: 1, h: 1, visible: true },
  { id: 'quality', type: 'quality_overview', title: '품질 현황', x: 2, y: 1, w: 1, h: 1, visible: true },
];

const STORAGE_KEY = 'ie-dashboard-layout';

interface DashboardState {
  widgets: DashboardWidget[];
  editMode: boolean;

  setEditMode: (v: boolean) => void;
  moveWidget: (id: string, x: number, y: number) => void;
  toggleWidget: (id: string) => void;
  resetLayout: () => void;
  hydrate: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  widgets: DEFAULT_WIDGETS,
  editMode: false,

  setEditMode: (v) => set({ editMode: v }),

  moveWidget: (id, x, y) => {
    const next = get().widgets.map((w) =>
      w.id === id ? { ...w, x, y } : w,
    );
    set({ widgets: next });
    _save(next);
  },

  toggleWidget: (id) => {
    const next = get().widgets.map((w) =>
      w.id === id ? { ...w, visible: !w.visible } : w,
    );
    set({ widgets: next });
    _save(next);
  },

  resetLayout: () => {
    set({ widgets: DEFAULT_WIDGETS });
    _save(DEFAULT_WIDGETS);
  },

  hydrate: () => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          set({ widgets: parsed });
        }
      }
    } catch {
      // 파싱 실패 시 기본 레이아웃 유지
    }
  },
}));

function _save(widgets: DashboardWidget[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(widgets));
  } catch {
    // 저장 실패 무시
  }
}
