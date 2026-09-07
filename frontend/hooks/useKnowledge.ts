'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getKnowledgeList, uploadKnowledge, deleteKnowledge } from '@/lib/api';
import {
  isCurrentAuthScope,
  protectedAuthMeta,
  runProtectedMutation,
  useAuthScope,
} from '@/components/Providers';
import { toast } from 'sonner';

export function useKnowledge() {
  const queryClient = useQueryClient();
  const authScope = useAuthScope();
  const knowledgeQueryKey = ['protected', authScope, 'knowledge'] as const;

  const listQuery = useQuery({
    queryKey: knowledgeQueryKey,
    queryFn: getKnowledgeList,
    staleTime: 60_000,
    meta: protectedAuthMeta(authScope),
  });

  const uploadMutation = useMutation({
    mutationKey: ['protected', authScope, 'knowledge', 'upload'],
    mutationFn: (file: File) =>
      runProtectedMutation(authScope, () => uploadKnowledge(file)),
    meta: protectedAuthMeta(authScope),
    onSuccess: (data) => {
      if (!isCurrentAuthScope(authScope)) return;
      void queryClient.invalidateQueries({ queryKey: knowledgeQueryKey });
      toast.success(`"${data.filename}" 업로드 완료 (${data.chunk_count}개 청크)`);
    },
    onError: (err: Error) => {
      if (!isCurrentAuthScope(authScope)) return;
      toast.error(err.message || '업로드 실패');
    },
  });

  const deleteMutation = useMutation({
    mutationKey: ['protected', authScope, 'knowledge', 'delete'],
    mutationFn: (docId: string) =>
      runProtectedMutation(authScope, () => deleteKnowledge(docId)),
    meta: protectedAuthMeta(authScope),
    onSuccess: () => {
      if (!isCurrentAuthScope(authScope)) return;
      void queryClient.invalidateQueries({ queryKey: knowledgeQueryKey });
      toast.success('문서 삭제 완료');
    },
    onError: (err: Error) => {
      if (!isCurrentAuthScope(authScope)) return;
      toast.error(err.message || '삭제 실패');
    },
  });

  return {
    documents: listQuery.data?.documents ?? [],
    isLoading: listQuery.isLoading,
    upload: uploadMutation.mutate,
    isUploading: uploadMutation.isPending,
    remove: deleteMutation.mutate,
    isDeleting: deleteMutation.isPending,
  };
}
