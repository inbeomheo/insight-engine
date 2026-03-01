'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Users, Trash2, UserPlus, Crown, Shield, Eye } from 'lucide-react';
import { useWorkspace } from '@/hooks/useWorkspace';
import { useUIStore } from '@/stores/uiStore';
import type { WorkspaceRole } from '@/lib/types';

const ROLE_LABELS: Record<WorkspaceRole, { label: string; icon: typeof Crown }> = {
  owner: { label: '소유자', icon: Crown },
  editor: { label: '편집자', icon: Shield },
  viewer: { label: '뷰어', icon: Eye },
};

export default function WorkspaceSettingsModal() {
  const { workspaceSettingsOpen, setWorkspaceSettingsOpen } = useUIStore();
  const {
    activeWorkspace,
    members,
    membersLoading,
    invite,
    inviting,
    removeMember: removeMemberFn,
    removing,
    deleteWorkspace: deleteWorkspaceFn,
    deleting,
  } = useWorkspace();

  const [email, setEmail] = useState('');
  const [role, setRole] = useState<string>('editor');
  const [confirmDelete, setConfirmDelete] = useState(false);

  const isOwner = activeWorkspace?.my_role === 'owner';

  function handleInvite() {
    const trimmed = email.trim();
    if (!trimmed) return;
    invite({ email: trimmed, role });
    setEmail('');
  }

  function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    deleteWorkspaceFn();
    setWorkspaceSettingsOpen(false);
    setConfirmDelete(false);
  }

  return (
    <Dialog
      open={workspaceSettingsOpen}
      onOpenChange={(v) => {
        setWorkspaceSettingsOpen(v);
        if (!v) setConfirmDelete(false);
      }}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            {activeWorkspace?.name ?? '워크스페이스'} 설정
          </DialogTitle>
          <DialogDescription>멤버를 관리하고 워크스페이스를 설정합니다</DialogDescription>
        </DialogHeader>

        {/* 멤버 초대 (owner만) */}
        {isOwner && (
          <div className="space-y-2">
            <label className="text-xs font-medium text-muted-foreground">멤버 초대</label>
            <div className="flex gap-2">
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="이메일 주소"
                className="flex-1 h-9 text-sm"
                onKeyDown={(e) => e.key === 'Enter' && handleInvite()}
              />
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger className="w-[100px] h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="editor">편집자</SelectItem>
                  <SelectItem value="viewer">뷰어</SelectItem>
                </SelectContent>
              </Select>
              <Button size="sm" className="h-9" onClick={handleInvite} disabled={inviting}>
                <UserPlus className="h-4 w-4 mr-1" />
                초대
              </Button>
            </div>
          </div>
        )}

        {/* 멤버 목록 */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-muted-foreground">
            멤버 ({members.length}명)
          </label>
          <div className="border rounded-lg divide-y max-h-[240px] overflow-y-auto">
            {membersLoading ? (
              <div className="p-4 text-center text-xs text-muted-foreground">불러오는 중...</div>
            ) : members.length === 0 ? (
              <div className="p-4 text-center text-xs text-muted-foreground">멤버가 없습니다</div>
            ) : (
              members.map((m) => {
                const roleInfo = ROLE_LABELS[m.role];
                const RoleIcon = roleInfo.icon;
                return (
                  <div key={m.user_id} className="flex items-center gap-3 px-3 py-2.5">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm truncate">
                        {m.email || m.user_id.slice(0, 8) + '...'}
                      </div>
                      <div className="flex items-center gap-1 text-[10px] text-muted-foreground/60">
                        <RoleIcon className="h-3 w-3" />
                        {roleInfo.label}
                        <span className="ml-1">
                          {new Date(m.joined_at).toLocaleDateString('ko-KR')}
                        </span>
                      </div>
                    </div>
                    {isOwner && m.role !== 'owner' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0"
                        disabled={removing}
                        onClick={() => removeMemberFn(m.user_id)}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-destructive/60" />
                      </Button>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 워크스페이스 삭제 (owner만) */}
        {isOwner && (
          <div className="pt-2 border-t">
            <Button
              variant="ghost"
              className="text-destructive text-xs"
              onClick={handleDelete}
              disabled={deleting}
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              {confirmDelete ? '정말 삭제하시겠습니까? 다시 클릭하면 삭제됩니다' : '워크스페이스 삭제'}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
