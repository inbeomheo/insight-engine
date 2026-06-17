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
    <header className="h-14 border-b border-border flex items-center justify-between px-4 shrink-0 bg-background/95" role="banner">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 hover:bg-accent"
          onClick={toggleSidebar}
          aria-label="메뉴 열기"
        >
          <Menu className="h-[18px] w-[18px]" />
        </Button>
        <div className="flex items-center gap-2">
          <div className="relative h-7 w-7 rounded-sm bg-foreground">
            <span className="absolute right-1.5 top-1.5 h-2.5 w-2.5 rounded-full bg-primary" />
            <Sparkles className="absolute bottom-1.5 left-1.5 h-3 w-3 text-background/80" />
          </div>
          <span className="font-bold text-[15px] tracking-tight text-foreground">
            Insight Engine
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1">
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
