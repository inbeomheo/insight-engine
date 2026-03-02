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
  McpPlugin,
  McpPublishRequest,
  McpPublishResponse,
  PipelineRequest,
  PipelineEvent,
  ScheduledPost,
  Workspace,
  WorkspaceMember,
  KnowledgeItem,
} from './types';
import { parseSSEStream } from './sse-parser';

const BASE = '';

const TIMEOUT_MS: Record<string, number> = {
  '/generate': 300_000,
  '/generate-batch': 660_000,
  '/api/generate-merged': 300_000,
  '/api/generate-multi': 300_000,
  '/api/generate-fusion': 300_000,
  '/api/mindmap': 60_000,
  '/api/export/docx': 30_000,
  '/api/providers': 10_000,
  '/api/playlist-videos': 30_000,
};
const DEFAULT_TIMEOUT_MS = 30_000;

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const timeoutMs = TIMEOUT_MS[url] ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // 외부 signal이 있으면 연동
  if (init?.signal) {
    init.signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const res = await fetch(`${BASE}${url}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
      signal: controller.signal,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    return res.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(`요청 시간이 초과되었습니다 (${Math.round(timeoutMs / 1000)}초). 네트워크 상태를 확인하거나 다시 시도해주세요.`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
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

  await parseSSEStream<StreamEvent>(
    res.body!.getReader(),
    onEvent,
    signal,
    () => onEvent({ type: 'error', error: '네트워크 연결이 끊겼습니다. 다시 시도해주세요.' })
  );
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

// 웹훅 테스트
export async function testWebhook(url: string): Promise<{ success: boolean; error?: string }> {
  return request('/api/webhook/test', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

// MCP 플러그인 목록
export async function getMcpPlugins(): Promise<{ plugins: McpPlugin[] }> {
  return request('/api/mcp/plugins');
}

// MCP 플러그인 발행
export async function publishToMcp(req: McpPublishRequest): Promise<McpPublishResponse> {
  return request('/api/mcp/publish', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

// 예약 발행 CRUD
export async function createSchedule(data: {
  title: string;
  content: string;
  html?: string;
  target_plugin: string;
  scheduled_at: string;
}): Promise<ScheduledPost> {
  return request('/api/schedule', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getSchedules(): Promise<{ schedules: ScheduledPost[] }> {
  return request('/api/schedule');
}

export async function deleteSchedule(postId: string): Promise<{ success: boolean }> {
  return request(`/api/schedule/${postId}`, { method: 'DELETE' });
}

// 파이프라인 실행 (SSE)
export async function runPipeline(
  req: PipelineRequest,
  onEvent: (event: PipelineEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE}/api/pipeline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }

  await parseSSEStream<PipelineEvent>(
    res.body!.getReader(),
    onEvent,
    signal,
    () => onEvent({ type: 'step_error', step: 'network', error: '네트워크 연결이 끊겼습니다.', progress: 0 })
  );
}

// =============================================
// 워크스페이스
// =============================================

export async function getWorkspaces(): Promise<{ workspaces: Workspace[] }> {
  return request('/api/workspaces');
}

export async function createWorkspace(name: string): Promise<Workspace> {
  return request('/api/workspaces', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export async function getWorkspaceMembers(
  workspaceId: string
): Promise<{ members: WorkspaceMember[] }> {
  return request(`/api/workspaces/${workspaceId}/members`);
}

export async function inviteMember(
  workspaceId: string,
  userEmail: string,
  role: string = 'editor'
): Promise<{ success: boolean; member?: WorkspaceMember }> {
  return request(`/api/workspaces/${workspaceId}/invite`, {
    method: 'POST',
    body: JSON.stringify({ user_email: userEmail, role }),
  });
}

export async function removeMember(
  workspaceId: string,
  userId: string
): Promise<{ success: boolean }> {
  return request(`/api/workspaces/${workspaceId}/members/${userId}`, {
    method: 'DELETE',
  });
}

export async function deleteWorkspace(
  workspaceId: string
): Promise<{ success: boolean }> {
  return request(`/api/workspaces/${workspaceId}`, {
    method: 'DELETE',
  });
}

// =============================================
// 지식 베이스 (RAG)
// =============================================

export async function uploadKnowledge(file: File): Promise<KnowledgeItem> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${BASE}/api/knowledge/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getKnowledgeList(): Promise<{ documents: KnowledgeItem[] }> {
  return request('/api/knowledge/list');
}

export async function deleteKnowledge(docId: string): Promise<{ success: boolean }> {
  return request(`/api/knowledge/${docId}`, { method: 'DELETE' });
}

// =============================================
// 프롬프트 템플릿 갤러리
// =============================================

export interface PromptTemplate {
  id: string;
  name: string;
  description: string;
  prompt_text: string;
  style_base: string;
  is_public: boolean;
  usage_count: number;
  created_at: string | null;
  updated_at: string | null;
  is_owner: boolean;
}

export interface TemplatesResponse {
  templates: PromptTemplate[];
  total: number;
  page: number;
  per_page: number;
  has_more: boolean;
}

export async function getTemplates(
  page = 1,
  search = ''
): Promise<TemplatesResponse> {
  const params = new URLSearchParams({ page: String(page) });
  if (search) params.set('search', search);
  return request(`/api/templates?${params}`);
}

export async function createTemplate(data: {
  name: string;
  description?: string;
  prompt_text: string;
  style_base?: string;
  is_public?: boolean;
}): Promise<PromptTemplate> {
  return request('/api/templates', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateTemplate(
  id: string,
  data: Partial<{
    name: string;
    description: string;
    prompt_text: string;
    style_base: string;
    is_public: boolean;
  }>
): Promise<PromptTemplate> {
  return request(`/api/templates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteTemplate(id: string): Promise<{ success: boolean }> {
  return request(`/api/templates/${id}`, { method: 'DELETE' });
}

export async function useTemplate(id: string): Promise<PromptTemplate> {
  return request(`/api/templates/${id}/use`, { method: 'POST' });
}

// =============================================
// 스타일 메모리
// =============================================

export interface StyleProfile {
  preferred_styles: Array<{ style_id: string; count: number }>;
  preferred_length: 'short' | 'medium' | 'long';
  preferred_writing_style: 'conversational' | 'explanatory' | 'casual' | 'expert';
  tone_keywords: string[];
  avoid_keywords: string[];
  custom_instructions: string;
  style_memory_enabled: boolean;
  generation_count: number;
}

export async function getStyleMemory(): Promise<{ profile: StyleProfile }> {
  return request('/api/user/style-memory');
}

export async function updateStyleMemory(prefs: {
  avoid_keywords?: string[];
  custom_instructions?: string;
  style_memory_enabled?: boolean;
}): Promise<{ success: boolean }> {
  return request('/api/user/style-memory', {
    method: 'PUT',
    body: JSON.stringify(prefs),
  });
}

export async function resetStyleMemory(): Promise<{ success: boolean }> {
  return request('/api/user/style-memory/reset', { method: 'POST' });
}

// === Video Q&A ===

export interface VideoQaMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface VideoQaSource {
  text: string;
  relevance: number;
}

export interface VideoQaResponse {
  answer: string;
  sources: VideoQaSource[];
}

export async function askVideoQuestion(
  videoUrl: string,
  question: string,
  history: VideoQaMessage[] = [],
  model?: string,
): Promise<VideoQaResponse> {
  return request('/api/video-qa', {
    method: 'POST',
    body: JSON.stringify({
      video_url: videoUrl,
      question,
      history,
      model,
    }),
  });
}
