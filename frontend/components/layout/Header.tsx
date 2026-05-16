'use client';

import { memo, useCallback } from 'react';
import { Menu, Settings, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useUIStore } from '@/stores/uiStore';

const Header = memo(function Header() {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const setSettingsModalOpen = useUIStore((s) => s.setSettingsModalOpen);
  const handleOpenSettings = useCallback(() => setSettingsModalOpen(true), [setSettingsModalOpen]);

  return (
    <header className="h-14 border-b border-border/60 flex items-center justify-between px-4 shrink-0 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-sm" role="banner">
      <div className="flex items-center gap-3">
        <Button
          id="menu-toggle-btn"
          variant="ghost"
          size="icon"
          className="h-9 w-9 hover:bg-accent"
          onClick={toggleSidebar}
          aria-label="메뉴 열기"
        >
          <Menu className="h-[18px] w-[18px]" />
        </Button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 gradient-primary rounded-lg flex items-center justify-center">
            <Sparkles className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="font-bold text-[15px] tracking-tight bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Insight Engine
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <Button
          id="settings-open-btn"
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
