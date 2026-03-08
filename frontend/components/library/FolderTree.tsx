'use client';

import { useState, useEffect, useCallback } from 'react';
import { Folder, FolderOpen, Plus, Trash2, ChevronRight, ChevronDown, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';

interface FolderItem {
  id: string;
  name: string;
  parent_id: string | null;
  content_count: number;
}

interface FolderTreeProps {
  selectedFolderId?: string | null;
  onSelectFolder?: (folderId: string | null) => void;
}

/** 폴더/카테고리 트리 사이드바 (F5-11) */
export default function FolderTree({ selectedFolderId, onSelectFolder }: FolderTreeProps) {
  const [folders, setFolders] = useState<FolderItem[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [newFolderName, setNewFolderName] = useState('');
  const [showNewFolder, setShowNewFolder] = useState(false);

  // 폴더 목록 로드
  const loadFolders = useCallback(async () => {
    try {
      const res = await fetch(apiUrl('/api/folders'));
      if (res.ok) {
        const data = await res.json();
        setFolders(data.folders || []);
      }
    } catch {
      // 로드 실패 무시
    }
  }, []);

  useEffect(() => {
    loadFolders();
  }, [loadFolders]);

  // 폴더 생성
  const createFolder = useCallback(async () => {
    const name = newFolderName.trim();
    if (!name) return;

    try {
      const res = await fetch(apiUrl('/api/folders'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      if (res.ok) {
        setNewFolderName('');
        setShowNewFolder(false);
        loadFolders();
      }
    } catch {
      // 생성 실패 무시
    }
  }, [newFolderName, loadFolders]);

  // 폴더 삭제
  const deleteFolder = useCallback(async (folderId: string) => {
    try {
      const res = await fetch(apiUrl(`/api/folders/${folderId}`), { method: 'DELETE' });
      if (res.ok) {
        if (selectedFolderId === folderId) onSelectFolder?.(null);
        loadFolders();
      }
    } catch {
      // 삭제 실패 무시
    }
  }, [selectedFolderId, onSelectFolder, loadFolders]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  // 루트 폴더만 (parent_id === null)
  const rootFolders = folders.filter((f) => !f.parent_id);

  return (
    <div className="space-y-2">
      {/* 헤더 */}
      <div className="flex items-center justify-between px-1">
        <span className="text-[11px] font-medium text-muted-foreground/60 uppercase tracking-wider">
          폴더
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-5 w-5 text-muted-foreground/40 hover:text-foreground"
          onClick={() => setShowNewFolder(!showNewFolder)}
          aria-label="새 폴더 추가"
        >
          <Plus className="h-3 w-3" />
        </Button>
      </div>

      {/* 새 폴더 입력 */}
      {showNewFolder && (
        <div className="flex items-center gap-1 px-1">
          <input
            type="text"
            value={newFolderName}
            onChange={(e) => setNewFolderName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && createFolder()}
            placeholder="폴더 이름..."
            className="flex-1 text-xs border border-border/40 rounded px-2 py-1 bg-white outline-none
                       focus:border-primary/40"
            autoFocus
          />
          <Button size="sm" className="h-6 text-[10px] px-2" onClick={createFolder}>
            추가
          </Button>
        </div>
      )}

      {/* 전체 (미분류) */}
      <button
        className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-colors ${
          selectedFolderId === null
            ? 'bg-primary/8 text-primary'
            : 'text-foreground/70 hover:bg-accent/50'
        }`}
        onClick={() => onSelectFolder?.(null)}
        aria-label="전체 폴더 보기"
      >
        <FileText className="h-3.5 w-3.5" />
        <span className="flex-1 text-left">전체</span>
      </button>

      {/* 폴더 목록 */}
      {rootFolders.map((folder) => {
        const isSelected = selectedFolderId === folder.id;
        const FolderIcon = isSelected ? FolderOpen : Folder;

        return (
          <div key={folder.id} className="group">
            <button
              className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs transition-colors ${
                isSelected
                  ? 'bg-primary/8 text-primary'
                  : 'text-foreground/70 hover:bg-accent/50'
              }`}
              onClick={() => onSelectFolder?.(folder.id)}
              aria-label={`${folder.name} 폴더 선택`}
            >
              <FolderIcon className="h-3.5 w-3.5 shrink-0" />
              <span className="flex-1 text-left truncate">{folder.name}</span>
              <span className="text-[10px] text-muted-foreground/40">{folder.content_count}</span>
              <button
                className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:text-destructive"
                onClick={(e) => { e.stopPropagation(); deleteFolder(folder.id); }}
                aria-label={`${folder.name} 폴더 삭제`}
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </button>
          </div>
        );
      })}
    </div>
  );
}
