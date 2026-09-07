'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchProviders } from '@/lib/api';
import { resolveModelSelection } from '@/lib/ai-model-selection';
import { useSettingsStore } from '@/stores/settingsStore';
import { useEffect } from 'react';
import { toast } from 'sonner';

export function useProviders() {
  const setProviders = useSettingsStore((state) => state.setProviders);
  const selectedModel = useSettingsStore((state) => state.selectedModel);

  const query = useQuery({
    queryKey: ['providers'],
    queryFn: fetchProviders,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    const providers = query.data?.providers;
    if (!providers) return;

    setProviders(providers);
    const models = Object.values(providers)[0]?.models ?? [];
    const resolvedModel = resolveModelSelection(models, selectedModel);
    if (resolvedModel && resolvedModel !== selectedModel) {
      // 자동 복원은 메모리에만 적용한다. 명시적 모델 선택만 기존 저장 경로를 사용한다.
      useSettingsStore.setState({ selectedModel: resolvedModel });
    }
  }, [query.data, selectedModel, setProviders]);

  useEffect(() => {
    if (query.error) {
      toast.error('AI 모델 목록을 불러올 수 없습니다');
    }
  }, [query.error]);

  return query;
}
