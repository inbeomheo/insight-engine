'use client';

import { useState, useEffect, useCallback, useRef, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import { Copy, FileCode, RefreshCw, Languages, ListCollapse } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useTranslation } from '@/hooks/useTranslation';

interface ContextMenuProps {
  /** 우클릭 감지할 컨테이너의 ref */
  containerRef: React.RefObject<HTMLElement | null>;
  /** 선택한 텍스트로 인라인 편집 요청 */
  onInlineEdit?: (text: string, action: string) => void;
}

interface MenuState {
  visible: boolean;
  x: number;
  y: number;
  selectedText: string;
}

const INITIAL: MenuState = { visible: false, x: 0, y: 0, selectedText: '' };

export default function ContextMenu({ containerRef, onInlineEdit }: ContextMenuProps) {
  const [menu, setMenu] = useState<MenuState>(INITIAL);
  const menuRef = useRef<HTMLDivElement>(null);
  const { t } = useTranslation();

  const handleContextMenu = useCallback((e: MouseEvent) => {
    const selection = window.getSelection()?.toString().trim();
    if (!selection) return; // 선택 없으면 기본 컨텍스트 메뉴 유지

    e.preventDefault();
    setMenu({
      visible: true,
      x: Math.min(e.clientX, window.innerWidth - 200),
      y: Math.min(e.clientY, window.innerHeight - 200),
      selectedText: selection,
    });
  }, []);

  const handleClose = useCallback(() => {
    setMenu(INITIAL);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    el.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('click', handleClose);
    document.addEventListener('scroll', handleClose, true);

    return () => {
      el.removeEventListener('contextmenu', handleContextMenu);
      document.removeEventListener('click', handleClose);
      document.removeEventListener('scroll', handleClose, true);
    };
  }, [containerRef, handleContextMenu, handleClose]);

  useEffect(() => {
    if (!menu.visible) return;
    const frame = requestAnimationFrame(() => {
      menuRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    });
    return () => cancelAnimationFrame(frame);
  }, [menu.visible]);

  const handleCopyText = () => {
    navigator.clipboard.writeText(menu.selectedText);
    toast.success(t('result.copied'));
    handleClose();
  };

  const handleCopyHtml = () => {
    const selection = window.getSelection();
    if (!selection?.rangeCount) return;

    const range = selection.getRangeAt(0);
    const div = document.createElement('div');
    div.appendChild(range.cloneContents());
    const html = div.innerHTML;

    navigator.clipboard.write([
      new ClipboardItem({
        'text/html': new Blob([html], { type: 'text/html' }),
        'text/plain': new Blob([menu.selectedText], { type: 'text/plain' }),
      }),
    ]);
    toast.success(t('result.richCopied'));
    handleClose();
  };

  const handleAction = (action: string) => {
    onInlineEdit?.(menu.selectedText, action);
    handleClose();
  };

  const handleMenuKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const items = Array.from(menuRef.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]') ?? []);
    if (event.key === 'Escape') {
      event.preventDefault();
      handleClose();
      return;
    }
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) || items.length === 0) return;
    event.preventDefault();
    const currentIndex = Math.max(0, items.indexOf(document.activeElement as HTMLButtonElement));
    const nextIndex =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? items.length - 1
          : (currentIndex + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
    items[nextIndex]?.focus();
  };

  if (!menu.visible) return null;

  const items = [
    { id: 'copy-text', icon: Copy, label: t('contextMenu.copyText'), onClick: handleCopyText },
    { id: 'copy-html', icon: FileCode, label: t('contextMenu.copyHtml'), onClick: handleCopyHtml },
    ...(onInlineEdit
      ? [
          { id: 'rewrite', icon: RefreshCw, label: t('contextMenu.rewriteSelection'), onClick: () => handleAction('rewrite') },
          { id: 'translate', icon: Languages, label: t('contextMenu.translateSelection'), onClick: () => handleAction('translate') },
          { id: 'summarize', icon: ListCollapse, label: t('contextMenu.summarizeSelection'), onClick: () => handleAction('summarize') },
        ]
      : []),
  ];

  return (
    <div
      ref={menuRef}
      data-testid="result-context-menu"
      className={cn(
        'fixed z-[70] min-w-[180px] py-1 bg-white dark:bg-zinc-800 rounded-lg shadow-lg border border-border/60',
        'animate-fade-in'
      )}
      style={{ top: menu.y, left: menu.x }}
      role="menu"
      aria-label="선택 텍스트 작업 메뉴"
      onKeyDown={handleMenuKeyDown}
    >
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.label}
            type="button"
            data-testid={`context-menu-item-${item.id}`}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-zinc-700 dark:text-zinc-200 hover:bg-muted/50 transition-colors text-left"
            onClick={item.onClick}
            role="menuitem"
            aria-label={item.label}
          >
            <Icon className="h-3.5 w-3.5 text-muted-foreground" />
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
