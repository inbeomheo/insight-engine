'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getKnowledgeList, uploadKnowledge, deleteKnowledge } from '@/lib/api';
import { toast } from 'sonner';

export function useKnowledge() {
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: ['knowledge'],
    queryFn: getKnowledgeList,
    staleTime: 60_000,
  });

  const uploadMutation = useMutation({
    mutationFn: uploadKnowledge,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['knowledge'] });
      toast.success(`"${data.filename}" 업로드 완료 (${data.chunk_count}개 청크)`);
    },
    onError: (err: Error) => {
      toast.error(err.message || '업로드 실패');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteKnowledge,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge'] });
      toast.success('문서 삭제 완료');
    },
    onError: (err: Error) => {
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
