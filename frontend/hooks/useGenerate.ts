'use client';

import { useState, useCallback, useRef, type Dispatch, type SetStateAction } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { generate, generateStream, generateBatch, generateMerged, generateFusion } from '@/lib/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useResultStore } from '@/stores/resultStore';
import { toast } from 'sonner';
import type { Report, StreamEvent } from '@/lib/types';
import { createReport, responseToReport } from '@/lib/report-factory';
import type { ExtractedMediaMeta } from '@/components/input/TextInput';

interface GenerateState {
  activeCount: number;
  isLoading: boolean;
  error: string | null;
}

const LOADING_TITLE = '생성 중...';
const FAILED_TITLE = '생성 실패';
const NO_RESULT_MESSAGE = '생성 결과를 받지 못했습니다.';
const UNKNOWN_ERROR_MESSAGE = '알 수 없는 오류';

type GenerateStreamRequest = Parameters<typeof generateStream>[0];
type GenerateResponseForReport = Parameters<typeof responseToReport>[0];

interface StreamRunnerOptions {
  req: GenerateStreamRequest;
  url: string;
  style: string;
  addReport: (report: Report) => void;
  updateReport: (id: string, partial: Partial<Report>) => void;
  removeReport: (id: string) => void;
  setState: Dispatch<SetStateAction<GenerateState>>;
  abortRef: { current: AbortController | null };
  buildMetaPatch: (event: StreamEvent) => Partial<Report>;
  buildResultReport: (event: StreamEvent, tempId: string, content: string) => Report;
}

async function runGenerateStream({
  req,
  url,
  style,
  addReport,
  updateReport,
  removeReport,
  setState,
  abortRef,
  buildMetaPatch,
  buildResultReport,
}: StreamRunnerOptions): Promise<boolean> {
  const tempId = crypto.randomUUID();
  addReport(createReport({
    id: tempId,
    url,
    title: LOADING_TITLE,
    content: '',
    html: '',
    style,
  }));

  let content = '';
  let succeeded = false;
  let finished = false;
  let rafId: number | null = null;
  const controller = new AbortController();
  abortRef.current = controller;

  const finish = (errorMessage?: string) => {
    if (finished) return;
    finished = true;
    setState((s) => {
      const c = Math.max(0, s.activeCount - 1);
      return { ...s, activeCount: c, isLoading: c > 0, error: errorMessage || null };
    });
  };

  const clearScheduledContentUpdate = () => {
    if (rafId !== null && typeof cancelAnimationFrame !== 'undefined') {
      cancelAnimationFrame(rafId);
    }
    rafId = null;
  };

  const scheduleContentUpdate = () => {
    if (rafId !== null) return;
    if (typeof requestAnimationFrame === 'undefined') {
      updateReport(tempId, { content });
      return;
    }
    rafId = requestAnimationFrame(() => {
      rafId = null;
      updateReport(tempId, { content });
    });
  };

  const hasMeaningfulContent = () => content.trim().length > 0;

  const fail = (message: string): false => {
    if (finished) return false;
    clearScheduledContentUpdate();
    if (hasMeaningfulContent()) {
      updateReport(tempId, { title: FAILED_TITLE, content });
    } else {
      removeReport(tempId);
    }
    finish(message);
    return false;
  };

  const cancel = (): boolean => {
    if (finished) return succeeded;
    clearScheduledContentUpdate();
    if (hasMeaningfulContent()) {
      updateReport(tempId, { content });
    } else {
      removeReport(tempId);
    }
    finish();
    return succeeded;
  };

  const succeed = (): true => {
    if (finished) return true;
    succeeded = true;
    finish();
    return true;
  };

  try {
    await generateStream(
      req,
      (event: StreamEvent) => {
        if (finished) return;

        if (event.type === 'meta') {
          updateReport(tempId, buildMetaPatch(event));
        } else if (event.type === 'delta' || event.type === 'token') {
          content += event.delta || event.data || '';
          scheduleContentUpdate();
        } else if (event.type === 'result') {
          content = event.content || content;
          clearScheduledContentUpdate();
          updateReport(tempId, buildResultReport(event, tempId, content));
          succeed();
        } else if (event.type === 'done') {
          content = event.content || content;
          clearScheduledContentUpdate();
          updateReport(tempId, {
            title: event.title || '생성 완료',
            content,
            html: event.html || event.data || '',
            usage: event.usage || { total_tokens: 0 },
            elapsed_time: event.elapsed_time || 0,
            prompt: event.prompt || '',
            cached: event.cached || false,
            comment_summary_included: event.comment_summary_included || false,
            seo: event.seo,
            faq_schema: event.faq_schema,
            cta: event.cta,
          });
          succeed();
        } else if (event.type === 'error') {
          fail(event.error || event.message || FAILED_TITLE);
        }
      },
      controller.signal,
    );

    if (!finished) {
      if (controller.signal.aborted) return cancel();
      return fail(NO_RESULT_MESSAGE);
    }
    return succeeded;
  } catch (err) {
    if (finished) return succeeded;
    if (controller.signal.aborted) return cancel();
    const message = err instanceof Error ? err.message : UNKNOWN_ERROR_MESSAGE;
    return fail(message);
  } finally {
    clearScheduledContentUpdate();
    if (abortRef.current === controller) abortRef.current = null;
  }
}

export function useGenerate() {
  const [state, setState] = useState<GenerateState>({
    activeCount: 0,
    isLoading: false,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);
  // 셀렉터 구독 — 스토어의 무관한 변경(테마, 사이드바 등)에 의한 리렌더 방지
  const { selectedModel, selectedStyle, modifiers, enableWebSearch, enableAgentMode, detailLevel, transcriptLanguage } = useSettingsStore(
    useShallow((s) => ({
      selectedModel: s.selectedModel,
      selectedStyle: s.selectedStyle,
      modifiers: s.modifiers,
      enableWebSearch: s.enableWebSearch,
      enableAgentMode: s.enableAgentMode,
      detailLevel: s.detailLevel,
      transcriptLanguage: s.transcriptLanguage,
    }))
  );
  const addReport = useResultStore((s) => s.addReport);
  const updateReport = useResultStore((s) => s.updateReport);
  const removeReport = useResultStore((s) => s.removeReport);

  const generateSingle = useCallback(
    async (url: string, useStreaming = false) => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return;
      }

      const streaming = useStreaming;

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      const req = { url, model: selectedModel, style: selectedStyle, modifiers, web_search: enableWebSearch, agent_mode: enableAgentMode, detail_level: detailLevel, transcript_language: transcriptLanguage };

      try {
        if (streaming) {
          await runGenerateStream({
            req,
            url,
            style: selectedStyle,
            addReport,
            updateReport,
            removeReport,
            setState,
            abortRef,
            buildMetaPatch: (event) => ({
              title: event.youtube_title || event.title || LOADING_TITLE,
              youtube_title: event.youtube_title || '',
              transcript_source: event.transcript_source || '',
            }),
            buildResultReport: (event, tempId, content) => responseToReport(
              { ...event, content: event.content || content } as GenerateResponseForReport,
              url,
              selectedStyle,
              { id: tempId },
            ),
          });
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
    [selectedModel, selectedStyle, modifiers, detailLevel, enableWebSearch, enableAgentMode, transcriptLanguage, addReport, updateReport, removeReport]
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
    async (
      text: string,
      mediaOrStreaming?: ExtractedMediaMeta | boolean,
      useStreaming = false,
    ): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }

      const streaming = typeof mediaOrStreaming === 'boolean' ? mediaOrStreaming : useStreaming;
      const media = typeof mediaOrStreaming === 'object' ? mediaOrStreaming : undefined;
      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));
      const req = {
        url: '',
        model: selectedModel,
        style: selectedStyle,
        modifiers,
        content: text,
        detail_level: detailLevel,
        ...(media || {}),
      };

      try {
        if (streaming) {
          return await runGenerateStream({
            req,
            url: '',
            style: selectedStyle,
            addReport,
            updateReport,
            removeReport,
            setState,
            abortRef,
            buildMetaPatch: (event) => ({
              title: event.source_title || event.title || LOADING_TITLE,
              transcript_source: event.transcript_source || '',
            }),
            buildResultReport: (event, tempId, content) => responseToReport(
              { ...event, content: event.content || content } as GenerateResponseForReport,
              '',
              selectedStyle,
              { id: tempId },
            ),
          });
        }

        const res = await generate(req);
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
    [selectedModel, selectedStyle, modifiers, detailLevel, addReport, updateReport, removeReport],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, activeCount: 0, isLoading: false }));
  }, []);

  return { ...state, generateSingle, generateFromText, generateBatchUrls, generateMergedUrls, generateFusionUrls, abort };
}
