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

      const ids = Object.keys(query.data.providers);
      if (ids.length === 0) return;

      // 선택된 프로바이더가 없거나 유효하지 않으면 첫 번째 프로바이더로 보정
      const fallbackProviderId = ids.includes('chatmock') ? 'chatmock' : ids.includes('zhipuai') ? 'zhipuai' : ids[0];
      const providerId = selectedProvider && ids.includes(selectedProvider) ? selectedProvider : fallbackProviderId;
      if (providerId !== selectedProvider) {
        setSelectedProvider(providerId);
      }

      // localStorage에 삭제된/구버전 모델이 남아 있으면 현재 프로바이더의 첫 모델로 보정
      const models = query.data.providers[providerId]?.models || [];
      const modelStillAvailable = models.some((model) => model.id === selectedModel);
      if (models.length > 0 && !modelStillAvailable) {
        setSelectedModel(models[0].id);
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
