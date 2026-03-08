/**
 * WebGPU 가속 추론 (F10-21)
 * 브라우저 WebGPU API를 이용한 로컬 LLM 추론
 * transformers.js (Hugging Face) 기반
 * 폴백: WebGL → CPU
 */

// ── 타입 정의 ─────────────────────────────────────────────────────────────────

// WebGPU 글로벌 타입 (런타임 브라우저 API — @webgpu/types 대체)
type GPUAdapter = { requestAdapterInfo(): Promise<{ vendor: string; device: string; architecture: string; description: string }> };

export type WebGPUStatus = 'unsupported' | 'available' | 'loading' | 'ready' | 'error';

export interface InferenceOptions {
  maxTokens?: number;
  temperature?: number;
  topP?: number;
}

export interface InferenceResult {
  text: string;
  tokens: number;
  latencyMs: number;
  backend: 'webgpu' | 'webgl' | 'cpu';
}

// ── WebGPU 가용성 체크 ────────────────────────────────────────────────────────

export async function checkWebGPUSupport(): Promise<{
  available: boolean;
  adapter: string | null;
  reason?: string;
}> {
  if (!('gpu' in navigator)) {
    return { available: false, adapter: null, reason: 'WebGPU API 미지원 (Chrome 113+ 필요)' };
  }

  try {
    const adapter = await (navigator as unknown as { gpu: { requestAdapter(): Promise<GPUAdapter | null> } }).gpu.requestAdapter();
    if (!adapter) {
      return { available: false, adapter: null, reason: 'GPU 어댑터를 찾을 수 없습니다' };
    }

    const info = await adapter.requestAdapterInfo();
    return {
      available: true,
      adapter: `${info.vendor} ${info.device}`.trim() || 'Unknown GPU',
    };
  } catch (e) {
    return {
      available: false,
      adapter: null,
      reason: `WebGPU 초기화 실패: ${e instanceof Error ? e.message : e}`,
    };
  }
}

// ── 경량 임베딩 모델 (로컬) ───────────────────────────────────────────────────

type TransformersModule = {
  pipeline: (task: string, model: string, options?: Record<string, unknown>) => Promise<{
    (text: string | string[], options?: Record<string, unknown>): Promise<Array<{ embedding?: number[]; [key: string]: unknown }>>;
  }>;
};

let _embeddingPipeline: ((text: string) => Promise<number[]>) | null = null;
let _pipelineLoading = false;

async function loadEmbeddingPipeline() {
  if (_embeddingPipeline) return _embeddingPipeline;
  if (_pipelineLoading) {
    // 로딩 중이면 대기
    await new Promise<void>(resolve => {
      const check = setInterval(() => {
        if (!_pipelineLoading) {
          clearInterval(check);
          resolve();
        }
      }, 100);
    });
    return _embeddingPipeline;
  }

  _pipelineLoading = true;
  try {
    // @xenova/transformers는 동적 import (번들 사이즈 최적화)
    const { pipeline } = await import('@xenova/transformers' as unknown as string) as unknown as TransformersModule;

    // WebGPU 지원 여부에 따라 디바이스 선택
    const support = await checkWebGPUSupport();
    const device = support.available ? 'webgpu' : 'cpu';

    const pipe = await pipeline(
      'feature-extraction',
      'Xenova/all-MiniLM-L6-v2',  // 경량 임베딩 모델 (22MB)
      { device }
    );

    _embeddingPipeline = async (text: string) => {
      const output = await pipe(text, { pooling: 'mean', normalize: true });
      return Array.from(output[0]?.embedding || []);
    };

    console.log(`[WebGPU] 임베딩 모델 로드 완료 (device: ${device})`);
    return _embeddingPipeline;
  } finally {
    _pipelineLoading = false;
  }
}

// ── 코사인 유사도 ─────────────────────────────────────────────────────────────

export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) throw new Error('벡터 차원이 다릅니다');
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

// ── 로컬 시맨틱 검색 ──────────────────────────────────────────────────────────

export interface SemanticSearchResult {
  index: number;
  score: number;
  text: string;
}

export async function localSemanticSearch(
  query: string,
  documents: string[],
  topK: number = 5,
): Promise<SemanticSearchResult[]> {
  const start = performance.now();

  let embedFn: ((text: string) => Promise<number[]>) | null;
  try {
    embedFn = await loadEmbeddingPipeline();
  } catch (e) {
    console.warn('[WebGPU] 임베딩 모델 로드 실패, 키워드 검색으로 폴백:', e);
    // 폴백: 단순 키워드 매칭
    const words = query.toLowerCase().split(/\s+/);
    return documents
      .map((doc, i) => ({
        index: i,
        text: doc,
        score: words.reduce((s, w) => s + (doc.toLowerCase().includes(w) ? 1 : 0), 0) / words.length,
      }))
      .filter(r => r.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, topK);
  }

  if (!embedFn) return [];

  const queryEmb = await embedFn(query);
  const docEmbs = await Promise.all(documents.map(doc => embedFn!(doc)));

  const results: SemanticSearchResult[] = documents.map((doc, i) => ({
    index: i,
    text: doc,
    score: cosineSimilarity(queryEmb, docEmbs[i]),
  }));

  results.sort((a, b) => b.score - a.score);
  const topResults = results.slice(0, topK);

  console.log(
    `[WebGPU] 시맨틱 검색 완료: ${documents.length}개 문서, ${(performance.now() - start).toFixed(0)}ms`
  );

  return topResults;
}

// ── React Hook ────────────────────────────────────────────────────────────────

import { useState, useEffect, useCallback } from 'react';

export function useWebGPU() {
  const [status, setStatus] = useState<WebGPUStatus>('unsupported');
  const [adapterInfo, setAdapterInfo] = useState<string | null>(null);

  useEffect(() => {
    checkWebGPUSupport().then(({ available, adapter }) => {
      setStatus(available ? 'available' : 'unsupported');
      setAdapterInfo(adapter);
    });
  }, []);

  const runSemanticSearch = useCallback(async (
    query: string,
    documents: string[],
    topK = 5
  ): Promise<SemanticSearchResult[]> => {
    if (status === 'unsupported') return [];
    setStatus('loading');
    try {
      const results = await localSemanticSearch(query, documents, topK);
      setStatus('ready');
      return results;
    } catch {
      setStatus('error');
      return [];
    }
  }, [status]);

  return { status, adapterInfo, runSemanticSearch };
}
