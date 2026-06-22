'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchProviders } from '@/lib/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useEffect } from 'react';
import { toast } from 'sonner';

export function useProviders() {
  const { setProviders, selectedProvider, selectedModel, setSelectedProvider, setSelectedModel } =
    useSettingsStore();

  const query = useQuery({
    queryKey: ['providers'],
    queryFn: fetchProviders,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (query.data?.providers) {
      setProviders(query.data.providers);

      // 선택된 프로바이더가 없거나 유효하지 않으면 첫 번째 선택
      const ids = Object.keys(query.data.providers);
      if (!selectedProvider || !ids.includes(selectedProvider)) {
        if (ids.length > 0) {
          setSelectedProvider(ids[0]);
          const firstModel = query.data.providers[ids[0]]?.models[0];
          if (firstModel) setSelectedModel(firstModel.id);
        }
      } else {
        // 프로바이더는 유효하지만 선택된 모델이 현재 목록에 없으면(모델 삭제/교체 등) 첫 모델로 교정
        const models = query.data.providers[selectedProvider]?.models ?? [];
        if (models.length > 0 && !models.some((m) => m.id === selectedModel)) {
          setSelectedModel(models[0].id);
        }
      }
    }
  }, [query.data, selectedProvider, selectedModel, setProviders, setSelectedProvider, setSelectedModel]);

  useEffect(() => {
    if (query.error) {
      toast.error('AI 모델 목록을 불러올 수 없습니다');
    }
  }, [query.error]);

  return query;
}
