'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getWorkspaces,
  createWorkspace,
  getWorkspaceMembers,
  inviteMember,
  removeMember,
  deleteWorkspace,
} from '@/lib/api';
import type { Workspace } from '@/lib/types';
import { toast } from 'sonner';

export function useWorkspace() {
  const queryClient = useQueryClient();
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);

  // 워크스페이스 목록
  const workspacesQuery = useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const data = await getWorkspaces();
      return data.workspaces;
    },
    staleTime: 60_000,
  });

  // 현재 워크스페이스
  const activeWorkspace = workspacesQuery.data?.find(
    (ws: Workspace) => ws.id === activeWorkspaceId
  ) ?? null;

  // 멤버 목록 (활성 워크스페이스가 있을 때만)
  const membersQuery = useQuery({
    queryKey: ['workspace-members', activeWorkspaceId],
    queryFn: async () => {
      if (!activeWorkspaceId) return [];
      const data = await getWorkspaceMembers(activeWorkspaceId);
      return data.members;
    },
    enabled: !!activeWorkspaceId,
    staleTime: 30_000,
  });

  // 생성
  const createMutation = useMutation({
    mutationFn: (name: string) => createWorkspace(name),
    onSuccess: (ws) => {
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      setActiveWorkspaceId(ws.id);
      toast.success('워크스페이스가 생성되었습니다.');
    },
    onError: (err: Error) => {
      toast.error(err.message || '워크스페이스 생성 실패');
    },
  });

  // 초대
  const inviteMutation = useMutation({
    mutationFn: ({ email, role }: { email: string; role: string }) => {
      if (!activeWorkspaceId) throw new Error('워크스페이스를 선택해주세요.');
      return inviteMember(activeWorkspaceId, email, role);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', activeWorkspaceId] });
      toast.success('멤버를 초대했습니다.');
    },
    onError: (err: Error) => {
      toast.error(err.message || '초대 실패');
    },
  });

  // 제거
  const removeMutation = useMutation({
    mutationFn: (userId: string) => {
      if (!activeWorkspaceId) throw new Error('워크스페이스를 선택해주세요.');
      return removeMember(activeWorkspaceId, userId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', activeWorkspaceId] });
      toast.success('멤버를 제거했습니다.');
    },
    onError: (err: Error) => {
      toast.error(err.message || '멤버 제거 실패');
    },
  });

  // 삭제
  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!activeWorkspaceId) throw new Error('워크스페이스를 선택해주세요.');
      return deleteWorkspace(activeWorkspaceId);
    },
    onSuccess: () => {
      setActiveWorkspaceId(null);
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
      toast.success('워크스페이스가 삭제되었습니다.');
    },
    onError: (err: Error) => {
      toast.error(err.message || '삭제 실패');
    },
  });

  const switchWorkspace = useCallback((id: string | null) => {
    setActiveWorkspaceId(id);
  }, []);

  return {
    workspaces: workspacesQuery.data ?? [],
    isLoading: workspacesQuery.isLoading,
    activeWorkspaceId,
    activeWorkspace,
    switchWorkspace,
    members: membersQuery.data ?? [],
    membersLoading: membersQuery.isLoading,
    create: createMutation.mutate,
    creating: createMutation.isPending,
    invite: inviteMutation.mutate,
    inviting: inviteMutation.isPending,
    removeMember: removeMutation.mutate,
    removing: removeMutation.isPending,
    deleteWorkspace: deleteMutation.mutate,
    deleting: deleteMutation.isPending,
  };
}
