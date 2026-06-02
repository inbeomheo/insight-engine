'use client';

import { memo, useCallback } from 'react';
import { Menu, PanelRight, Settings, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores/uiStore';

interface HeaderProps {
  modelLabel?: string;
  isLoading?: boolean;
  sourceCount?: number;
  onOpenRightPanel?: () => void;
}

const Header = memo(function Header({ modelLabel = '자동 선택', isLoading = false, sourceCount = 0, onOpenRightPanel }: HeaderProps) {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const setSettingsModalOpen = useUIStore((s) => s.setSettingsModalOpen);
  const handleOpenSettings = useCallback(() => setSettingsModalOpen(true), [setSettingsModalOpen]);
  const statusLabel = isLoading ? '생성 중' : sourceCount > 0 ? '생성 준비' : '소스 대기';

  return (
    <header className="h-16 border-b border-white/70 flex items-center justify-between gap-3 px-4 shrink-0 bg-white/75 dark:bg-zinc-900/80 backdrop-blur-xl" role="banner">
      <div className="flex min-w-0 items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 hover:bg-accent"
          onClick={toggleSidebar}
          aria-label="메뉴 열기"
        >
          <Menu className="h-[18px] w-[18px]" />
        </Button>
        <div className="flex min-w-0 items-center gap-2">
          <div className="w-7 h-7 gradient-primary rounded-lg flex items-center justify-center">
            <Sparkles className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="truncate font-bold text-[15px] tracking-tight bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Insight Studio
          </span>
        </div>
      </div>

      <div className="hidden min-w-0 flex-1 items-center justify-center gap-2 md:flex">
        <span data-testid="header-model-badge" className="max-w-[260px] truncate rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          모델 {modelLabel}
        </span>
        <span data-testid="header-status-badge" className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
          {statusLabel}
        </span>
      </div>

      <div className="flex items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          data-testid="mobile-right-panel-trigger"
          className="h-9 gap-1.5 rounded-xl px-2 text-xs xl:hidden"
          onClick={onOpenRightPanel}
          aria-label="작업 패널 열기"
        >
          <PanelRight className="h-[18px] w-[18px]" />
          <span className="hidden sm:inline">작업</span>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 hover:bg-accent"
          onClick={handleOpenSettings}
          aria-label="설정 열기"
        >
          <Settings className="h-[18px] w-[18px]" />
        </Button>
      </div>
    </header>
  );
});

export default Header;
