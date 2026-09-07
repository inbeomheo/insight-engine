'use client';

import { useState, useCallback, useEffect, useRef, type Dispatch, type SetStateAction } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { generate, generateStream, generateBatch, generateMerged, generateFusion } from '@/lib/api';
import { useSettingsStore } from '@/stores/settingsStore';
import { useResultStore } from '@/stores/resultStore';
import { toast } from 'sonner';
import type { Report, StreamEvent } from '@/lib/types';
import { createReport, responseToReport } from '@/lib/report-factory';
import { getAuthSession } from '@/lib/auth-session';
import { useAuthUserId } from '@/hooks/useAuthUserId';

interface GenerateState {
  activeCount: number;
  isLoading: boolean;
  error: string | null;
}

export interface BatchGenerationOutcome {
  succeededUrls: string[];
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
  requestUserId: string | null;
}

function currentAuthUserId(): string | null {
  return getAuthSession()?.user.id ?? null;
}

function isCurrentAuthUser(requestUserId: string | null): boolean {
  return currentAuthUserId() === requestUserId;
}

function settleGeneration(
  setState: Dispatch<SetStateAction<GenerateState>>,
  requestUserId: string | null,
  error: string | null,
): boolean {
  if (!isCurrentAuthUser(requestUserId)) return false;
  setState((state) => {
    const activeCount = Math.max(0, state.activeCount - 1);
    return { ...state, activeCount, isLoading: activeCount > 0, error };
  });
  return true;
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
  requestUserId,
}: StreamRunnerOptions): Promise<boolean> {
  const tempId = crypto.randomUUID();
  addReport(createReport({
    id: tempId,
    is_streaming: true,
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
    if (!isCurrentAuthUser(requestUserId)) return;
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
      if (isCurrentAuthUser(requestUserId)) updateReport(tempId, { content });
      return;
    }
    rafId = requestAnimationFrame(() => {
      rafId = null;
      if (!isCurrentAuthUser(requestUserId)) return;
      updateReport(tempId, { content });
    });
  };

  const hasMeaningfulContent = () => content.trim().length > 0;

  const fail = (message: string): false => {
    if (finished) return false;
    clearScheduledContentUpdate();
    if (!isCurrentAuthUser(requestUserId)) {
      finish();
    } else if (hasMeaningfulContent()) {
      updateReport(tempId, { title: FAILED_TITLE, content, is_streaming: false });
    } else {
      removeReport(tempId);
    }
    finish(message);
    return false;
  };

  const cancel = (): boolean => {
    if (finished) return succeeded;
    clearScheduledContentUpdate();
    if (!isCurrentAuthUser(requestUserId)) {
      finish();
    } else if (hasMeaningfulContent()) {
      updateReport(tempId, { content, is_streaming: false });
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
        if (!isCurrentAuthUser(requestUserId)) {
          controller.abort();
          finish();
          return;
        }

        if (event.type === 'meta') {
          updateReport(tempId, buildMetaPatch(event));
        } else if (event.type === 'delta' || event.type === 'token') {
          content += event.delta || event.data || '';
          scheduleContentUpdate();
        } else if (event.type === 'result') {
          content = event.content || content;
          clearScheduledContentUpdate();
          updateReport(tempId, {
            ...buildResultReport(event, tempId, content),
            is_streaming: false,
          });
          succeed();
        } else if (event.type === 'done') {
          content = event.content || content;
          clearScheduledContentUpdate();
          updateReport(tempId, {
            title: event.title || '생성 완료',
            content,
            html: event.html || event.data || '',
            is_streaming: false,
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
      if (!isCurrentAuthUser(requestUserId)) {
        finish();
        return false;
      }
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
  const authUserId = useAuthUserId();

  useEffect(() => {
    abortRef.current?.abort();
    // 이전 계정의 진행 상태를 새 계정 UI에 넘기지 않는다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState({ activeCount: 0, isLoading: false, error: null });
  }, [authUserId]);
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
    async (url: string, useStreaming = false): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }

      const streaming = useStreaming;
      const requestUserId = currentAuthUserId();

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      const req = { url, model: selectedModel, style: selectedStyle, modifiers, web_search: enableWebSearch, agent_mode: enableAgentMode, detail_level: detailLevel, transcript_language: transcriptLanguage };

      try {
        if (streaming) {
          return await runGenerateStream({
            req,
            url,
            style: selectedStyle,
            addReport,
            updateReport,
            removeReport,
            setState,
            abortRef,
            requestUserId,
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
          if (!isCurrentAuthUser(requestUserId)) return false;
          const report = responseToReport(res, url, selectedStyle);
          addReport(report);
          settleGeneration(setState, requestUserId, null);
          return true;
        }
      } catch (err) {
        if (!isCurrentAuthUser(requestUserId)) return false;
        const message = err instanceof Error ? err.message : '알 수 없는 오류';
        settleGeneration(setState, requestUserId, message);
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, detailLevel, enableWebSearch, enableAgentMode, transcriptLanguage, addReport, updateReport, removeReport]
  );

  const generateBatchUrls = useCallback(
    async (urls: string[]): Promise<BatchGenerationOutcome> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return { succeededUrls: [] };
      }
      if (urls.length === 0) return { succeededUrls: [] };

      // 단일 URL이면 일반 생성
      if (urls.length === 1) {
        const succeeded = await generateSingle(urls[0], false);
        return { succeededUrls: succeeded ? [urls[0]] : [] };
      }

      const requestUserId = currentAuthUserId();
      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      try {
        const res = await generateBatch(urls, selectedModel, selectedStyle, modifiers, undefined, {
          detail_level: detailLevel,
          transcript_language: transcriptLanguage,
          enable_web_search: enableWebSearch,
          enable_agent_mode: enableAgentMode,
        });
        if (!isCurrentAuthUser(requestUserId)) return { succeededUrls: [] };
        let ts = Date.now();
        const succeededUrls: string[] = [];
        const failures: string[] = [];

        for (const url of urls) {
          const item = res.results.find((result) => result.url === url);
          if (item?.success) {
            const report = responseToReport(item, item.url, selectedStyle, { createdAt: ts++ });
            addReport(report);
            succeededUrls.push(url);
          } else {
            failures.push(`${url}: ${item?.error || NO_RESULT_MESSAGE}`);
          }
        }

        if (failures.length > 0 && succeededUrls.length > 0) {
          toast.warning(`${failures.length}개 URL 처리 실패`, {
            description: failures.join('\n'),
          });
        } else if (succeededUrls.length === 0) {
          settleGeneration(setState, requestUserId, `모든 URL 처리에 실패했습니다.\n${failures.join('\n')}`);
          return { succeededUrls: [] };
        }

        settleGeneration(setState, requestUserId, null);
        return { succeededUrls };
      } catch (err) {
        if (!isCurrentAuthUser(requestUserId)) return { succeededUrls: [] };
        const message = err instanceof Error ? err.message : '배치 생성 실패';
        settleGeneration(setState, requestUserId, message);
        return { succeededUrls: [] };
      }
    },
    [selectedModel, selectedStyle, modifiers, detailLevel, transcriptLanguage, enableWebSearch, enableAgentMode, addReport, generateSingle]
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

      const requestUserId = currentAuthUserId();
      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      try {
        const res = await generateMerged(urls, selectedModel, selectedStyle, modifiers, undefined, transcriptLanguage);
        if (!isCurrentAuthUser(requestUserId)) return false;
        const report = responseToReport(res, urls[0], selectedStyle, {
          id: res.id || crypto.randomUUID(),
          youtube_title: res.source_videos?.[0]?.title || '',
          transcript_source: res.source_videos?.[0]?.transcript_source || '',
          merged: true,
          source_videos: res.source_videos,
        });
        addReport(report);
        settleGeneration(setState, requestUserId, null);
        return true;
      } catch (err) {
        if (!isCurrentAuthUser(requestUserId)) return false;
        const message = err instanceof Error ? err.message : '합쳐서 생성 실패';
        settleGeneration(setState, requestUserId, message);
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, transcriptLanguage, addReport]
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

      const requestUserId = currentAuthUserId();
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
        if (!isCurrentAuthUser(requestUserId)) return false;

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
        settleGeneration(setState, requestUserId, null);
        return true;
      } catch (err) {
        if (!isCurrentAuthUser(requestUserId)) return false;
        const message = err instanceof Error ? err.message : '퓨전 분석 실패';
        settleGeneration(setState, requestUserId, message);
        return false;
      }
    },
    [selectedModel, selectedStyle, modifiers, addReport]
  );

  const generateFromText = useCallback(
    async (text: string, useStreaming = false): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }

      const streaming = useStreaming;
      const requestUserId = currentAuthUserId();
      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));
      const req = {
        url: '',
        model: selectedModel,
        style: selectedStyle,
        modifiers,
        content: text,
        detail_level: detailLevel,
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
            requestUserId,
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
        if (!isCurrentAuthUser(requestUserId)) return false;
        const report = responseToReport(res, '', selectedStyle);
        addReport(report);
        settleGeneration(setState, requestUserId, null);
        return true;
      } catch (err) {
        if (!isCurrentAuthUser(requestUserId)) return false;
        const message = err instanceof Error ? err.message : '알 수 없는 오류';
        settleGeneration(setState, requestUserId, message);
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
