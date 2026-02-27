'use client';

import { useState, useCallback, useRef } from 'react';
import { generate, generateStream, generateBatch, generateMerged, generateFusion } from '@/lib/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useResultStore } from '@/stores/resultStore';
import { toast } from 'sonner';
import type { Report, StreamEvent } from '@/lib/types';

interface GenerateState {
  isLoading: boolean;
  streamingReportId: string | null;
  streamContent: string;
  error: string | null;
}

export function useGenerate() {
  const [state, setState] = useState<GenerateState>({
    isLoading: false,
    streamingReportId: null,
    streamContent: '',
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  const { selectedModel, selectedStyle, modifiers } = useSettingsStore();
  const { addReport, updateReport } = useResultStore();

  const generateSingle = useCallback(
    async (url: string, useStreaming = false) => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return;
      }

      setState({ isLoading: true, streamingReportId: null, streamContent: '', error: null });

      const req = { url, model: selectedModel, style: selectedStyle, modifiers };

      try {
        if (useStreaming) {
          // 스트리밍 모드
          const tempId = crypto.randomUUID();
          const tempReport: Report = {
            id: tempId,
            url,
            youtube_title: '',
            title: '생성 중...',
            content: '',
            html: '',
            style: selectedStyle,
            prompt: '',
            usage: { total_tokens: 0 },
            elapsed_time: 0,
            transcript_source: '',
            cached: false,
            comment_summary_included: false,
            time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
            createdAt: Date.now(),
          };
          addReport(tempReport);
          setState((s) => ({ ...s, streamingReportId: tempId }));

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
                setState((s) => ({ ...s, streamContent: content }));
                updateReport(tempId, { content });
              } else if (event.type === 'done') {
                updateReport(tempId, {
                  content,
                  html: event.data || '',
                  usage: event.usage || { total_tokens: 0 },
                  elapsed_time: event.elapsed_time || 0,
                  prompt: event.prompt || '',
                  cached: event.cached || false,
                  comment_summary_included: event.comment_summary_included || false,
                  seo: event.seo,
                });
                setState({ isLoading: false, streamingReportId: null, streamContent: '', error: null });
              } else if (event.type === 'error') {
                setState((s) => ({ ...s, isLoading: false, error: event.error || '생성 실패' }));
              }
            },
            controller.signal
          );
        } else {
          // 비스트리밍 모드
          const res = await generate(req);
          const report: Report = {
            id: crypto.randomUUID(),
            url,
            youtube_title: res.youtube_title || '',
            title: res.title,
            content: res.content,
            html: res.html,
            style: selectedStyle,
            prompt: res.prompt,
            usage: res.usage,
            elapsed_time: res.elapsed_time,
            transcript_source: res.transcript_source,
            cached: res.cached,
            comment_summary_included: res.comment_summary_included,
            seo: res.seo,
            time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
            createdAt: Date.now(),
          };
          addReport(report);
          setState({ isLoading: false, streamingReportId: null, streamContent: '', error: null });
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : '알 수 없는 오류';
        setState((s) => ({ ...s, isLoading: false, error: message }));
      }
    },
    [selectedModel, selectedStyle, modifiers, addReport, updateReport]
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

      setState({ isLoading: true, streamingReportId: null, streamContent: '', error: null });

      try {
        const res = await generateBatch(urls, selectedModel, selectedStyle, modifiers);
        let ts = Date.now();
        const failedUrls: string[] = [];

        for (const item of res.results) {
          if (item.success) {
            const report: Report = {
              id: crypto.randomUUID(),
              url: item.url,
              youtube_title: item.youtube_title || '',
              title: item.title,
              content: item.content,
              html: item.html,
              style: selectedStyle,
              prompt: item.prompt || '',
              usage: item.usage || { total_tokens: 0 },
              elapsed_time: item.elapsed_time || 0,
              transcript_source: item.transcript_source || '',
              cached: item.cached || false,
              comment_summary_included: item.comment_summary_included || false,
              seo: item.seo,
              time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
              createdAt: ts++,
            };
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
          setState((s) => ({ ...s, isLoading: false, error: '모든 URL 처리에 실패했습니다.' }));
          return false;
        }

        setState({ isLoading: false, streamingReportId: null, streamContent: '', error: null });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '배치 생성 실패';
        setState((s) => ({ ...s, isLoading: false, error: message }));
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

      setState({ isLoading: true, streamingReportId: null, streamContent: '', error: null });

      try {
        const res = await generateMerged(urls, selectedModel, selectedStyle, modifiers);
        const report: Report = {
          id: res.id || crypto.randomUUID(),
          url: urls[0],
          youtube_title: res.source_videos?.[0]?.title || '',
          title: res.title,
          content: res.content,
          html: res.html,
          style: selectedStyle,
          prompt: res.prompt || '',
          usage: res.usage || { total_tokens: 0 },
          elapsed_time: res.elapsed_time || 0,
          transcript_source: res.source_videos?.[0]?.transcript_source || '',
          cached: false,
          comment_summary_included: res.comment_summary_included || false,
          seo: res.seo,
          time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
          createdAt: Date.now(),
          merged: true,
          source_videos: res.source_videos,
        };
        addReport(report);
        setState({ isLoading: false, streamingReportId: null, streamContent: '', error: null });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '합쳐서 생성 실패';
        setState((s) => ({ ...s, isLoading: false, error: message }));
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

      setState({ isLoading: true, streamingReportId: null, streamContent: '', error: null });

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

        const report: Report = {
          id: crypto.randomUUID(),
          url: urls[0],
          youtube_title: '',
          title: result.title,
          content: result.content,
          html: result.html,
          style: selectedStyle,
          prompt: '',
          usage: { total_tokens: result.usage.total_tokens },
          elapsed_time: result.fusion_meta.processing_time,
          transcript_source: '',
          cached: false,
          comment_summary_included: false,
          time: new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
          createdAt: Date.now(),
          isFusion: true,
          fusionMeta: result.fusion_meta,
          sections: result.sections,
        };
        addReport(report);
        setState({ isLoading: false, streamingReportId: null, streamContent: '', error: null });
        return true;
      } catch (err) {
        const message = err instanceof Error ? err.message : '퓨전 분석 실패';
        setState((s) => ({ ...s, isLoading: false, error: message }));
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, addReport]
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, isLoading: false }));
  }, []);

  return { ...state, generateSingle, generateBatchUrls, generateMergedUrls, generateFusionUrls, abort };
}
