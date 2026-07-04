'use client';

import { useState, useCallback, useRef } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { generate, generateStream, generateBatch, generateMerged, generateFusion } from '@/lib/api';
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

  const generateSingle = useCallback(
    async (url: string, useStreaming = false) => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return;
      }

      // 로컬(Ollama) 모델은 CPU 추론으로 느릴 수 있어 스트리밍을 사용 —
      // 5분 타임아웃으로 끊기는 대신 토큰을 즉시 표시한다.
      const streaming = useStreaming || selectedModel.startsWith('ollama');

      setState((s) => ({ ...s, activeCount: s.activeCount + 1, isLoading: true, error: null }));

      const req = { url, model: selectedModel, style: selectedStyle, modifiers, web_search: enableWebSearch, agent_mode: enableAgentMode, detail_level: detailLevel, transcript_language: transcriptLanguage };

      try {
        if (streaming) {
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
              } else if (event.type === 'delta' || event.type === 'token') {
                content += event.delta || event.data || '';
                // rAF throttle: 프레임당 1회만 store 업데이트 (메인 스레드 블로킹 방지)
                if (!rafRef.current) {
                  rafRef.current = true;
                  requestAnimationFrame(() => {
                    updateReport(tempId, { content });
                    rafRef.current = false;
                  });
                }
              } else if (event.type === 'result') {
                // 최종 파싱 결과로 교체해 비스트리밍 경로와 동일한 Report 형태를 유지
                content = event.content || content;
                rafRef.current = false;
                const finalReport = responseToReport(event as unknown as Parameters<typeof responseToReport>[0], url, selectedStyle, {
                  id: tempId,
                });
                updateReport(tempId, finalReport);
                setState((s) => { const c = s.activeCount - 1; return { ...s, activeCount: c, isLoading: c > 0, error: null }; });
              } else if (event.type === 'done') {
                // rAF 대기 중인 업데이트 취소 — done에서 최종 content 반영
                rafRef.current = false;
                updateReport(tempId, {
                  title: event.title || '생성 완료',
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
                setState((s) => { const c = Math.max(0, s.activeCount - 1); return { ...s, activeCount: c, isLoading: c > 0, error: event.error || event.message || '생성 실패' }; });
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
    [selectedModel, selectedStyle, modifiers, detailLevel, enableWebSearch, enableAgentMode, transcriptLanguage, addReport, updateReport]
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
    async (text: string, useStreaming = false): Promise<boolean> => {
      if (!selectedModel) {
        setState((s) => ({ ...s, error: 'AI 모델을 선택해주세요.' }));
        return false;
      }

      const streaming = useStreaming || selectedModel.startsWith('ollama');
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
          const tempId = crypto.randomUUID();
          const tempReport: Report = createReport({
            id: tempId,
            url: '',
            title: '생성 중...',
            content: '',
            html: '',
            style: selectedStyle,
          });
          addReport(tempReport);

          let content = '';
          let succeeded = false;
          let finished = false;
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

          await generateStream(
            req,
            (event: StreamEvent) => {
              if (event.type === 'meta') {
                updateReport(tempId, {
                  title: event.source_title || event.title || '생성 중...',
                  transcript_source: event.transcript_source || '',
                });
              } else if (event.type === 'delta' || event.type === 'token') {
                content += event.delta || event.data || '';
                if (!rafRef.current) {
                  rafRef.current = true;
                  requestAnimationFrame(() => {
                    updateReport(tempId, { content });
                    rafRef.current = false;
                  });
                }
              } else if (event.type === 'result') {
                content = event.content || content;
                rafRef.current = false;
                const finalReport = responseToReport(event as unknown as Parameters<typeof responseToReport>[0], '', selectedStyle, {
                  id: tempId,
                });
                updateReport(tempId, finalReport);
                succeeded = true;
                finish();
              } else if (event.type === 'error') {
                rafRef.current = false;
                finish(event.error || event.message || '생성 실패');
              }
            },
            controller.signal,
          );

          if (!finished) finish(succeeded ? undefined : '생성 결과를 받지 못했습니다.');
          return succeeded;
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
    [selectedModel, selectedStyle, modifiers, detailLevel, addReport, updateReport],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setState((s) => ({ ...s, activeCount: 0, isLoading: false }));
  }, []);

  return { ...state, generateSingle, generateFromText, generateBatchUrls, generateMergedUrls, generateFusionUrls, abort };
}
