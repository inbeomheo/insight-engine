'use client';

import { useState, useCallback, useRef } from 'react';
import { runPipeline } from '@/lib/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useResultStore } from '@/stores/resultStore';
import type { PipelineStep, PipelineEvent } from '@/lib/types';
import { responseToReport } from '@/lib/report-factory';

/** 블로그 자동화 파이프라인의 초기 스텝 */
const INITIAL_STEPS: PipelineStep[] = [
  { id: 'transcript', name: '자막 추출', description: 'YouTube 자막과 댓글을 가져옵니다', progress: 0, status: 'pending' },
  { id: 'generate', name: '콘텐츠 생성', description: 'AI가 블로그 글을 작성합니다', progress: 0, status: 'pending' },
  { id: 'seo', name: 'SEO 최적화', description: 'SEO/GEO 메타데이터를 추출합니다', progress: 0, status: 'pending' },
];

interface PipelineState {
  isRunning: boolean;
  steps: PipelineStep[];
  progress: number;
  error: string | null;
}

export function usePipeline() {
  const [state, setState] = useState<PipelineState>({
    isRunning: false,
    steps: INITIAL_STEPS,
    progress: 0,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const { selectedModel, selectedStyle, modifiers } = useSettingsStore();
  const { addReport } = useResultStore();

  const startPipeline = useCallback(
    async (url: string, pipelineId = 'blog_automation') => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return;
      }

      const controller = new AbortController();
      abortRef.current = controller;

      setState({
        isRunning: true,
        steps: INITIAL_STEPS.map((s) => ({ ...s })),
        progress: 0,
        error: null,
      });

      try {
        await runPipeline(
          {
            pipeline_id: pipelineId,
            url,
            model: selectedModel,
            style: selectedStyle,
            modifiers,
          },
          (event: PipelineEvent) => {
            setState((prev) => {
              const steps = [...prev.steps];

              if (event.type === 'step_start') {
                const idx = steps.findIndex((s) => s.id === event.step);
                if (idx >= 0) {
                  steps[idx] = { ...steps[idx], status: 'running' };
                }
                return { ...prev, steps, progress: event.progress };
              }

              if (event.type === 'step_complete') {
                const idx = steps.findIndex((s) => s.id === event.step);
                if (idx >= 0) {
                  steps[idx] = {
                    ...steps[idx],
                    status: 'done',
                    elapsed: event.elapsed,
                    progress: 1,
                  };
                }
                return { ...prev, steps, progress: event.progress };
              }

              if (event.type === 'step_error') {
                const idx = steps.findIndex((s) => s.id === event.step);
                if (idx >= 0) {
                  steps[idx] = {
                    ...steps[idx],
                    status: 'error',
                    error: event.error,
                  };
                }
                return { ...prev, steps, isRunning: false, error: event.error || '스텝 실행 실패' };
              }

              if (event.type === 'pipeline_complete') {
                const result = event.result;
                if (result) {
                  addReport(responseToReport(result, url, selectedStyle));
                }
                return { ...prev, steps, progress: 1, isRunning: false, error: null };
              }

              return prev;
            });
          },
          controller.signal
        );
      } catch (err) {
        if (controller.signal.aborted) return;
        const message = err instanceof Error ? err.message : '파이프라인 실행 실패';
        setState((s) => ({ ...s, isRunning: false, error: message }));
      }
    },
    [selectedModel, selectedStyle, modifiers, addReport]
  );

  const cancelPipeline = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isRunning: false }));
  }, []);

  return { ...state, startPipeline, cancelPipeline };
}
