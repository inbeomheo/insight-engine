'use client';

import { useState, useCallback, useRef } from 'react';
import {
  generate,
  generateStream,
  generateBatch,
  generateMerged,
  generateFusion,
  generateFromFile as apiGenerateFromFile,
  generateFromAudio as apiGenerateFromAudio,
} from '@/lib/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useResultStore } from '@/stores/resultStore';
import { toast } from 'sonner';
import type { Report, StreamEvent } from '@/lib/types';
import { createReport, responseToReport } from '@/lib/report-factory';

interface GenerateState {
  activeCount: number;
  isLoading: boolean;
  error: string | null;
}

export function useGenerate() {
  const [state, setState] = useState<GenerateState>({
    activeCount: 0,
    isLoading: false,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const rafRef = useRef(false);
  const { selectedModel, selectedStyle, modifiers, enableWebSearch, enableAgentMode, detailLevel } = useSettingsStore();
  const { addReport, updateReport } = useResultStore();

  const generateSingle = useCallback(
    async (url: string, useStreaming = false) => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return;
      }

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      const req = { url, model: selectedModel, style: selectedStyle, modifiers, web_search: enableWebSearch, agent_mode: enableAgentMode, detail_level: detailLevel };

      try {
        if (useStreaming) {
          // 스트리밍 모드
          const tempId = crypto.randomUUID();
          const tempReport: Report = createReport({
            id: tempId, url, title: '생성 중...', content: '', html: '', style: selectedStyle,
          });
          addReport(tempReport);

          let content = '';
          const controller = new AbortController();
          abortRef.current = controller;

          await generateStream(
            req,
            (event: StreamEvent) => {
              if (event.type === 'meta') {
                updateReport(tempId, {
                  title: event.title || '생성 중...',
                  youtube_title: event.youtube_title || '',
                  transcript_source: event.transcript_source || '',
                });
              } else if (event.type === 'token') {
                content += event.data || '';
                // rAF throttle: 프레임당 1회만 store 업데이트 (메인 스레드 블로킹 방지)
                if (!rafRef.current) {
                  rafRef.current = true;
                  requestAnimationFrame(() => {
                    updateReport(tempId, { content });
                    rafRef.current = false;
                  });
                }
              } else if (event.type === 'done') {
                // rAF 대기 중인 업데이트 취소 — done에서 최종 content 반영
                rafRef.current = false;
                updateReport(tempId, {
                  content,
                  html: event.data || '',
                  usage: event.usage || { total_tokens: 0 },
                  elapsed_time: event.elapsed_time || 0,
                  prompt: event.prompt || '',
                  cached: event.cached || false,
                  comment_summary_included: event.comment_summary_included || false,
                  seo: event.seo,
                  faq_schema: event.faq_schema,
                  cta: event.cta,
                });
                setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
              } else if (event.type === 'error') {
                rafRef.current = false;
                setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: event.error || '생성 실패' }; });
              }
            },
            controller.signal
          );
        } else {
          // 비스트리밍 모드
          const res = await generate(req);
          const report = responseToReport(res, url, selectedStyle);
          addReport(report);
          setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : '알 수 없는 오류';
        setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: message }; });
      }
    },
    [selectedModel, selectedStyle, modifiers, detailLevel, enableWebSearch, enableAgentMode, addReport, updateReport]
  );

  const generateBatchUrls = useCallback(
    async (urls: string[]): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }
      if (urls.length === 0) return false;

      // 단일 URL이면 일반 생성
      if (urls.length === 1) {
        await generateSingle(urls[0], false);
        return true;
      }

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      try {
        const res = await generateBatch(urls, selectedModel, selectedStyle, modifiers);
        let ts = Date.now();
        const failedUrls: string[] = [];

        for (const item of res.results) {
          if (item.success) {
            const report = responseToReport(item, item.url, selectedStyle, { createdAt: ts++ });
            addReport(report);
          } else {
            failedUrls.push(item.url);
          }
        }

        if (failedUrls.length > 0 && failedUrls.length < urls.length) {
          toast.warning(`${failedUrls.length}개 URL 처리 실패`, {
            description: failedUrls.map((u) => u.slice(0, 60)).join('\n'),
          });
        } else if (failedUrls.length === urls.length) {
          setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: '모든 URL 처리에 실패했습니다.' }; });
          return false;
        }

        setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '배치 생성 실패';
        setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: message }; });
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, addReport, generateSingle]
  );

  const generateMergedUrls = useCallback(
    async (urls: string[]): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }
      if (urls.length < 2) {
        setState((s) => ({ ...s, error: '합쳐서 생성은 최소 2개 URL이 필요합니다.' }));
        return false;
      }

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      try {
        const res = await generateMerged(urls, selectedModel, selectedStyle, modifiers);
        const report = responseToReport(res, urls[0], selectedStyle, {
          id: res.id || crypto.randomUUID(),
          youtube_title: res.source_videos?.[0]?.title || '',
          transcript_source: res.source_videos?.[0]?.transcript_source || '',
          merged: true,
          source_videos: res.source_videos,
        });
        addReport(report);
        setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '합쳐서 생성 실패';
        setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: message }; });
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, addReport]
  );

  const generateFusionUrls = useCallback(
    async (urls: string[]): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }
      if (urls.length < 2) {
        setState((s) => ({ ...s, error: '퓨전 분석은 최소 2개 URL이 필요합니다.' }));
        return false;
      }

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      try {
        const { enableWebResearch, enableDeepComments } = useSettingsStore.getState();
        const result = await generateFusion({
          urls,
          style: selectedStyle,
          model: selectedModel,
          modifiers,
          enable_web_research: enableWebResearch,
          enable_deep_comments: enableDeepComments,
        });

        const report = createReport({
          url: urls[0],
          title: result.title,
          content: result.content,
          html: result.html,
          style: selectedStyle,
          usage: { total_tokens: result.usage.total_tokens },
          elapsed_time: result.fusion_meta.processing_time,
          isFusion: true,
          fusionMeta: result.fusion_meta,
          sections: result.sections,
        });
        addReport(report);
        setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '퓨전 분석 실패';
        setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: message }; });
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, addReport]
  );

  const generateFromText = useCallback(
    async (text: string): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      try {
        const res = await generate({
          url: '',
          model: selectedModel,
          style: selectedStyle,
          modifiers,
          content: text,
        });
        const report = responseToReport(res, '', selectedStyle);
        addReport(report);
        setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '알 수 없는 오류';
        setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: message }; });
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, addReport],
  );

  const generateFromFile = useCallback(
    async (file: File): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      try {
        const res = await apiGenerateFromFile(file, {
          model: selectedModel,
          style: selectedStyle,
          modifiers,
          detail_level: detailLevel,
        });
        addReport(responseToReport(res, `file:${file.name}`, selectedStyle));
        setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '파일 생성 실패';
        setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: message }; });
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, detailLevel, addReport],
  );

  const generateFromAudio = useCallback(
    async (file: File): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      try {
        const res = await apiGenerateFromAudio(file, {
          model: selectedModel,
          style: selectedStyle,
          modifiers,
          detail_level: detailLevel,
        });
        addReport(responseToReport(res, `audio:${file.name}`, selectedStyle));
        setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '음성 생성 실패';
        setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: message }; });
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, detailLevel, addReport],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, activeCount: 0, isLoading: false }));
  }, []);

  return { ...state, generateSingle, generateFromText, generateFromFile, generateFromAudio, generateBatchUrls, generateMergedUrls, generateFusionUrls, abort };
}
