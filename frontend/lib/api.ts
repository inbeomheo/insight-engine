import type {
  GenerateRequest,
  GenerateResponse,
  ProvidersResponse,
  MindmapResponse,
  PlaylistResponse,
  MultiStyleResponse,
  StreamEvent,
  Modifiers,
  SourceVideo,
  FusionMeta,
  FusionSections,
} from './types';

const BASE = '';

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json();
}

// 프로바이더/모델 목록
export async function fetchProviders(): Promise<ProvidersResponse> {
  return request('/api/providers');
}

// 단일 생성
export async function generate(req: GenerateRequest): Promise<GenerateResponse> {
  return request('/generate', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

// 스트리밍 생성
export async function generateStream(
  req: GenerateRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE}/generate-stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: StreamEvent = JSON.parse(line.slice(6));
          onEvent(event);
        } catch {
          // JSON 파싱 실패 무시
        }
      }
    }
  }
}

// 배치 생성
export async function generateBatch(
  urls: string[],
  model: string,
  style: string,
  modifiers: GenerateRequest['modifiers'],
  customPrompt?: string
) {
  return request<{ results: Array<GenerateResponse & { url: string; success: boolean }> }>(
    '/generate-batch',
    {
      method: 'POST',
      body: JSON.stringify({ urls, model, style, modifiers, customPrompt }),
    }
  );
}

// 합쳐서 생성 (N개 URL → 1개 통합 카드)
export interface MergedGenerateResponse extends GenerateResponse {
  id: string;
  merged: boolean;
  source_videos: SourceVideo[];
}

export async function generateMerged(
  urls: string[],
  model: string,
  style: string,
  modifiers: Modifiers,
  customPrompt?: string
): Promise<MergedGenerateResponse> {
  return request('/api/generate-merged', {
    method: 'POST',
    body: JSON.stringify({ urls, model, style, modifiers, customPrompt }),
  });
}

// 멀티 스타일 생성
export async function generateMulti(
  url: string,
  model: string,
  styles: string[]
): Promise<MultiStyleResponse> {
  return request('/api/generate-multi', {
    method: 'POST',
    body: JSON.stringify({ url, model, styles }),
  });
}

// 마인드맵
export async function generateMindmap(
  content: string,
  title: string,
  model?: string
): Promise<MindmapResponse> {
  return request('/api/mindmap', {
    method: 'POST',
    body: JSON.stringify({ content, title, model }),
  });
}

// 재생목록 영상 추출
export async function fetchPlaylistVideos(
  url: string,
  maxResults = 10
): Promise<PlaylistResponse> {
  return request('/api/playlist-videos', {
    method: 'POST',
    body: JSON.stringify({ url, maxResults }),
  });
}

// DOCX 내보내기
export async function exportDocx(title: string, content: string): Promise<Blob> {
  const res = await fetch(`${BASE}/api/export/docx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, content }),
  });
  if (!res.ok) throw new Error('DOCX 내보내기 실패');
  return res.blob();
}

// 퓨전 분석
export interface FusionRequest {
  urls: string[];
  style: string;
  model: string;
  modifiers?: Modifiers;
  enable_web_research?: boolean;
  enable_deep_comments?: boolean;
}

export interface FusionResponse {
  title: string;
  content: string;
  html: string;
  sections: FusionSections;
  fusion_meta: FusionMeta;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
}

export async function generateFusion(req: FusionRequest): Promise<FusionResponse> {
  return request('/api/generate-fusion', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

// 캐시 삭제
export async function clearCache(): Promise<void> {
  await request('/api/cache/clear', { method: 'POST' });
}
