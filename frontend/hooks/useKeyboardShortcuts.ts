'use client';

import { useEffect, useMemo } from 'react';
import { useUIStore } from '@/stores/uiStore';

/** 단축키 정의 */
interface ShortcutDef {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  label: string;
  category: string;
  action: () => void;
}

/** 글로벌 키보드 단축키 훅 (F5-07) */
export function useKeyboardShortcuts() {
  const {
    setSettingsModalOpen,
    toggleSidebar,
    setActiveView,
  } = useUIStore();

  const shortcuts: ShortcutDef[] = useMemo(() => [
    // 설정
    { key: ',', ctrl: true, label: '설정 열기', category: '일반', action: () => setSettingsModalOpen(true) },
    { key: 'b', ctrl: true, label: '사이드바 토글', category: '일반', action: () => toggleSidebar() },
    // 탐색
    { key: '1', alt: true, label: '메인 뷰', category: '탐색', action: () => setActiveView('main') },
    { key: '2', alt: true, label: '캘린더 뷰', category: '탐색', action: () => setActiveView('calendar') },
  ], [setSettingsModalOpen, toggleSidebar, setActiveView]);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // 입력 필드에서는 단축키 무시
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      for (const s of shortcuts) {
        const ctrlMatch = s.ctrl ? (e.ctrlKey || e.metaKey) : !(e.ctrlKey || e.metaKey);
        const shiftMatch = s.shift ? e.shiftKey : !e.shiftKey;
        const altMatch = s.alt ? e.altKey : !e.altKey;

        if (e.key === s.key && ctrlMatch && shiftMatch && altMatch) {
          e.preventDefault();
          s.action();
          return;
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);

  return shortcuts;
}
