'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchProviders } from '@/lib/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useEffect } from 'react';
import { toast } from 'sonner';

function collectModels(providers: NonNullable<Awaited<ReturnType<typeof fetchProviders>>['providers']>) {
  return Object.values(providers).flatMap((provider) => provider.models ?? []);
}

export function useProviders() {
  const { setProviders, selectedModel, setSelectedModel } = useSettingsStore();

  const query = useQuery({
    queryKey: ['providers'],
    queryFn: fetchProviders,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    const providers = query.data?.providers;
    if (!providers) return;

    setProviders(providers);
    const models = collectModels(providers);
    if (models.length > 0 && !models.some((model) => model.id === selectedModel)) {
      setSelectedModel(models[0].id);
    }
  }, [query.data, selectedModel, setProviders, setSelectedModel]);

  useEffect(() => {
    if (query.error) {
      toast.error('AI 모델 목록을 불러올 수 없습니다');
    }
  }, [query.error]);

  return query;
}
