'use client';

import { useState } from 'react';
import { ChevronDown, Plus, Users, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useWorkspace } from '@/hooks/useWorkspace';
import { useUIStore } from '@/stores/uiStore';
import { cn } from '@/lib/utils';

export default function WorkspaceSelector() {
  const {
    workspaces,
    activeWorkspaceId,
    activeWorkspace,
    switchWorkspace,
    create,
    creating,
  } = useWorkspace();
  const { setWorkspaceSettingsOpen } = useUIStore();

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');

  function handleCreate() {
    const name = newName.trim();
    if (!name) return;
    create(name);
    setNewName('');
    setShowCreate(false);
  }

  const displayName = activeWorkspace?.name ?? '개인';

  return (
    <div className="px-3 pb-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="w-full justify-between h-9 px-2.5 text-xs font-medium text-foreground/80 hover:bg-white hover:shadow-sm"
          >
            <span className="flex items-center gap-2 truncate">
              <Users className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
              <span className="truncate">{displayName}</span>
            </span>
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0" />
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="start" className="w-[230px]">
          {/* 개인 (null workspace) */}
          <DropdownMenuItem
            className={cn(!activeWorkspaceId && 'bg-accent')}
            onClick={() => switchWorkspace(null)}
          >
            <span className="truncate">개인</span>
          </DropdownMenuItem>

          {workspaces.length > 0 && <DropdownMenuSeparator />}

          {/* 워크스페이스 목록 */}
          {workspaces.map((ws) => (
            <DropdownMenuItem
              key={ws.id}
              className={cn(activeWorkspaceId === ws.id && 'bg-accent')}
              onClick={() => switchWorkspace(ws.id)}
            >
              <span className="truncate">{ws.name}</span>
              <span className="ml-auto text-[10px] text-muted-foreground/50">
                {ws.my_role === 'owner' ? '소유자' : ws.my_role === 'editor' ? '편집자' : '뷰어'}
              </span>
            </DropdownMenuItem>
          ))}

          <DropdownMenuSeparator />

          {/* 새 워크스페이스 */}
          {showCreate ? (
            <div className="p-2 space-y-2" onClick={(e) => e.stopPropagation()}>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="워크스페이스 이름"
                className="h-8 text-xs"
                maxLength={50}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleCreate();
                  if (e.key === 'Escape') setShowCreate(false);
                }}
              />
              <div className="flex gap-1.5">
                <Button size="sm" className="h-7 flex-1 text-xs" onClick={handleCreate} disabled={creating}>
                  만들기
                </Button>
                <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setShowCreate(false)}>
                  취소
                </Button>
              </div>
            </div>
          ) : (
            <DropdownMenuItem onClick={() => setShowCreate(true)}>
              <Plus className="h-3.5 w-3.5 mr-2" />
              새 워크스페이스
            </DropdownMenuItem>
          )}

          {/* 설정 (활성 워크스페이스가 있을 때만) */}
          {activeWorkspace && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setWorkspaceSettingsOpen(true)}>
                <Settings className="h-3.5 w-3.5 mr-2" />
                워크스페이스 설정
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
