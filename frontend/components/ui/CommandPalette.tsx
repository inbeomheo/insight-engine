'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search, FileText, Settings, Download, Plus,
  BarChart3, BookOpen, Globe
} from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';


interface Command {
  id: string;
  label: string;
  icon: typeof Search;
  category: string;
  action: () => void;
  keywords?: string[];
}

/** 커맨드 팔레트 (F5-01) — Cmd+K로 열기 */
export default function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const {
    setSettingsModalOpen,
    setPlaylistModalOpen,
    setTemplateGalleryOpen,
  } = useUIStore();

  const commands: Command[] = [
    {
      id: 'new-content',
      label: '새 콘텐츠 생성',
      icon: Plus,
      category: '생성',
      action: () => { setOpen(false); router.push('/'); },
      keywords: ['생성', 'create', 'new'],
    },
    {
      id: 'open-notes',
      label: 'LLMWiki 열기',
      icon: BookOpen,
      category: '탐색',
      action: () => { setOpen(false); router.push('/notes'); },
      keywords: ['노트', 'notes', 'wiki', '지식'],
    },
    {
      id: 'open-settings',
      label: '설정 열기',
      icon: Settings,
      category: '설정',
      action: () => { setOpen(false); setSettingsModalOpen(true); },
      keywords: ['설정', 'settings', 'config'],
    },
    {
      id: 'open-playlist',
      label: '재생목록 가져오기',
      icon: Globe,
      category: '도구',
      action: () => { setOpen(false); setPlaylistModalOpen(true); },
      keywords: ['재생목록', 'playlist', 'youtube'],
    },
    {
      id: 'open-templates',
      label: '템플릿 갤러리',
      icon: FileText,
      category: '도구',
      action: () => { setOpen(false); setTemplateGalleryOpen(true); },
      keywords: ['템플릿', 'template', 'gallery'],
    },
    {
      id: 'open-dashboard',
      label: '운영 대시보드',
      icon: BarChart3,
      category: '탐색',
      action: () => { setOpen(false); router.push('/dashboard'); },
      keywords: ['대시보드', 'dashboard', 'stats', '운영'],
    },
    {
      id: 'export-help',
      label: '내보내기 안내',
      icon: Download,
      category: '도구',
      action: () => { setOpen(false); router.push('/'); },
      keywords: ['내보내기', 'export', 'download', 'html', 'markdown'],
    },
  ];

  // 필터링
  const filtered = query.trim()
    ? commands.filter((cmd) => {
        const q = query.toLowerCase();
        return (
          cmd.label.toLowerCase().includes(q) ||
          cmd.keywords?.some((k) => k.toLowerCase().includes(q))
        );
      })
    : commands;

  // Cmd+K / Ctrl+K 단축키
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setOpen(false);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // 열릴 때 포커스
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // 키보드 네비게이션
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && filtered[selectedIndex]) {
        e.preventDefault();
        filtered[selectedIndex].action();
      }
    },
    [filtered, selectedIndex],
  );

  // 선택 인덱스가 범위를 벗어나면 리셋
  useEffect(() => {
    if (selectedIndex >= filtered.length) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedIndex(Math.max(0, filtered.length - 1));
    }
  }, [filtered.length, selectedIndex]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* 배경 오버레이 */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* 팔레트 */}
      <div className="relative w-full max-w-lg mx-4 bg-white rounded-xl shadow-2xl border border-border/60 overflow-hidden animate-in fade-in slide-in-from-top-4 duration-200">
        {/* 검색 입력 */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border/60">
          <Search className="h-4 w-4 text-muted-foreground/60 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            onKeyDown={handleKeyDown}
            placeholder="명령어 검색..."
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/40"
          />
          <kbd className="text-[10px] text-muted-foreground/50 bg-muted/50 px-1.5 py-0.5 rounded font-mono">
            ESC
          </kbd>
        </div>

        {/* 명령어 목록 */}
        <div ref={listRef} className="max-h-[300px] overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <p className="px-4 py-6 text-sm text-muted-foreground/60 text-center">
              일치하는 명령어가 없습니다
            </p>
          ) : (
            filtered.map((cmd, idx) => {
              const Icon = cmd.icon;
              return (
                <button
                  key={cmd.id}
                  className={`w-full flex items-center gap-3 px-4 py-2.5 text-left text-sm transition-colors ${
                    idx === selectedIndex
                      ? 'bg-primary/8 text-primary'
                      : 'text-foreground hover:bg-accent/50'
                  }`}
                  onClick={cmd.action}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <Icon className="h-4 w-4 shrink-0 opacity-60" />
                  <span className="flex-1">{cmd.label}</span>
                  <span className="text-[10px] text-muted-foreground/40">
                    {cmd.category}
                  </span>
                </button>
              );
            })
          )}
        </div>

        {/* 하단 힌트 */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-border/40 text-[10px] text-muted-foreground/40">
          <span>
            <kbd className="font-mono bg-muted/50 px-1 rounded">↑↓</kbd> 이동
          </span>
          <span>
            <kbd className="font-mono bg-muted/50 px-1 rounded">Enter</kbd> 실행
          </span>
          <span>
            <kbd className="font-mono bg-muted/50 px-1 rounded">Esc</kbd> 닫기
          </span>
        </div>
      </div>
    </div>
  );
}
