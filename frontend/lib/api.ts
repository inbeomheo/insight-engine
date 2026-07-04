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
  VideoEvent,
  EventSummary,
  QaCheckResponse,
  ProviderValidateResponse,
  FactCheckResponse,
  SeoOptimizeResponse,
  PlagiarismResponse,
  ReadabilityResponse,
  SentimentFlowResponse,
  SharePageResponse,
  JobResponse,
} from './types';
import { parseSSEStream } from './sse-parser';

/** Flask 백엔드 직접 호출 (Next.js 프록시 우회) */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

/** 직접 fetch 호출 시 사용하는 URL 빌더 */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

const BASE = API_BASE;

const TIMEOUT_MS: Record<string, number> = {
  '/generate': 300_000,
  '/generate-batch': 660_000,
  '/api/generate-merged': 300_000,
  '/api/generate-multi': 300_000,
  '/api/generate-fusion': 300_000,
  '/api/mindmap': 60_000,
  '/api/export/docx': 30_000,
  '/api/shares': 15_000,
  '/api/providers': 10_000,
  '/api/playlist-videos': 30_000,
  '/api/chat': 60_000,
  '/api/support/chat': 30_000,
  '/api/video-deepdives/extract': 660_000,
  '/api/extract-pdf': 60_000,
};
const DEFAULT_TIMEOUT_MS = 30_000;

const SUPPORT_SESSION_KEY = 'insight-engine-support-session-id';

function getSupportSessionId(): string {
  if (typeof window === 'undefined') return 'server';
  let sessionId = localStorage.getItem(SUPPORT_SESSION_KEY);
  if (!sessionId) {
    sessionId = `sess_${crypto.randomUUID()}`;
    localStorage.setItem(SUPPORT_SESSION_KEY, sessionId);
  }
  return sessionId;
}

function supportHeaders(): HeadersInit {
  return { 'X-Support-Session-Id': getSupportSessionId() };
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const timeoutMs = TIMEOUT_MS[url] ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  // 외부 signal이 있으면 연동
  if (init?.signal) {
    init.signal.addEventListener('abort', () => controller.abort());
  }

  // FormData일 때는 Content-Type 헤더 생략 (브라우저가 boundary 자동 설정)
  const isFormData = init?.body instanceof FormData;
  const headers = isFormData ? undefined : { 'Content-Type': 'application/json' };

  try {
    const mergedHeaders = {
      ...headers,
      ...(init?.headers || {}),
    };
    const res = await fetch(`${BASE}${url}`, {
      ...init,
      headers: mergedHeaders,
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

/** Blob 응답 전용 (DOCX/PDF 등 바이너리 다운로드) */
async function requestBlob(url: string, init?: RequestInit): Promise<Blob> {
  const timeoutMs = TIMEOUT_MS[url] ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

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
    return res.blob();
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new Error(`요청 시간이 초과되었습니다 (${Math.round(timeoutMs / 1000)}초).`);
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

export interface ExtractPdfResponse {
  text: string;
  truncated: boolean;
  pages: number;
}

export async function extractPdf(file: File): Promise<ExtractPdfResponse> {
  const formData = new FormData();
  formData.append('file', file);
  return request('/api/extract-pdf', {
    method: 'POST',
    body: formData,
  });
}

export async function getJob(jobId: string): Promise<JobResponse> {
  return request(`/api/jobs/${jobId}`);
}

export async function createSharePage(req: {
  title: string;
  content: string;
  html?: string;
  url?: string;
  style?: string;
}): Promise<SharePageResponse> {
  return request('/api/shares', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export interface VideoDeepDiveSlide {
  idx: number;
  t: number;
  mmss?: string;
  title?: string;
  note?: string;
  img?: string;
  suggestion?: string;
  source?: string;
}

export interface VideoDeepDiveItem {
  id: string;
  title: string;
  youtube_id: string;
  source_url: string;
  created: string;
  slide_count: number;
  slides: VideoDeepDiveSlide[];
  visual_suggestions: Array<{
    idx: number;
    kind: 'photo' | 'screenshot';
    label?: string;
    description: string;
    section?: string;
  }>;
  tags: string[];
}

export interface VideoDeepDiveResponse {
  slug: string;
  meta: VideoDeepDiveItem;
  body: string;
}

export async function createVideoDeepDiveFromResult(req: {
  video_id?: string;
  url?: string;
  source_url?: string;
  title: string;
  content: string;
  transcript?: string;
  transcript_segments?: Array<{ start: number; text: string }>;
  slides?: VideoDeepDiveSlide[];
}): Promise<{ item: VideoDeepDiveItem; viewer_url: string }> {
  return request('/api/video-deepdives/from-result', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function extractVideoDeepDiveScreenshots(req: {
  video_id?: string;
  url?: string;
  title?: string;
  content?: string;
  transcript?: string;
  max_slides?: number;
  scene_threshold?: number;
  min_gap?: number;
}): Promise<{ meta: VideoDeepDiveItem; slides: VideoDeepDiveSlide[]; viewer_url: string }> {
  return request('/api/video-deepdives/extract', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function fetchVideoDeepDive(videoId: string): Promise<VideoDeepDiveResponse> {
  return request(`/api/video-deepdives/${encodeURIComponent(videoId)}`);
}

export async function updateVideoDeepDiveSlides(
  videoId: string,
  slides: VideoDeepDiveSlide[],
): Promise<{ ok: boolean; item: VideoDeepDiveItem }> {
  return request(`/api/video-deepdives/${encodeURIComponent(videoId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ slides }),
  });
}

/** 파일 업로드용 FormData 빌더 (generateFromFile/Audio 공용) */
function buildFileFormData(
  file: File,
  opts: { model: string; style: string; modifiers?: Modifiers; customPrompt?: string; detail_level?: string },
): FormData {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('model', opts.model);
  fd.append('style', opts.style);
  if (opts.modifiers) fd.append('modifiers', JSON.stringify(opts.modifiers));
  if (opts.customPrompt) fd.append('customPrompt', opts.customPrompt);
  if (opts.detail_level) fd.append('detail_level', opts.detail_level);
  return fd;
}

// 파일 업로드 생성 (PDF/DOCX)
export async function generateFromFile(
  file: File,
  opts: { model: string; style: string; modifiers?: Modifiers; customPrompt?: string; detail_level?: string },
): Promise<GenerateResponse> {
  return request('/generate', { method: 'POST', body: buildFileFormData(file, opts) });
}

// 오디오 파일 업로드 생성 (음성 메모, 팟캐스트 녹음)
export async function generateFromAudio(
  file: File,
  opts: { model: string; style: string; modifiers?: Modifiers; customPrompt?: string; detail_level?: string },
): Promise<GenerateResponse> {
  return request('/generate', { method: 'POST', body: buildFileFormData(file, opts) });
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
  return requestBlob('/api/export/docx', { method: 'POST', body: JSON.stringify({ title, content }) });
}

// 포맷별 내보내기 (MD, TXT, ZIP)
export async function exportFormat(format: 'markdown' | 'txt' | 'zip', title: string, content: string): Promise<Blob> {
  return requestBlob(`/api/export/${format}`, { method: 'POST', body: JSON.stringify({ title, content }) });
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
  await request('/api/cache', { method: 'DELETE' });
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

// === TTS (팟캐스트 변환) ===

/**
 * 텍스트를 TTS로 변환해 오디오 Blob을 반환합니다.
 * @param text 변환할 텍스트 (마크다운 포함 가능)
 * @param voice 목소리 식별자
 * @param speed 재생 속도 (0.5~2.0)
 */
export async function synthesizeTts(
  text: string,
  voice = 'alloy',
  speed = 1.0,
): Promise<Blob> {
  const res = await fetch(`${BASE}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice, speed }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `TTS 오류: HTTP ${res.status}`);
  }
  return res.blob();
}

// === 이벤트 추출 ===

export interface ExtractEventsRequest {
  url?: string;
  transcript?: string;
  model?: string;
}

export interface ExtractEventsResponse {
  events: VideoEvent[];
  categorized: Record<string, VideoEvent[]>;
  summary: EventSummary;
}

export async function extractEvents(req: ExtractEventsRequest): Promise<ExtractEventsResponse> {
  return request('/api/extract-events', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

// === QA 게이트 ===

export async function qaCheck(
  content: string,
  rules?: { forbidden_words?: string[] },
): Promise<QaCheckResponse> {
  return request('/api/qa-check', {
    method: 'POST',
    body: JSON.stringify({ content, rules }),
  });
}

// === 프로바이더 유효성 검사 (F18) ===

export async function validateProvider(
  providerId: string,
  apiKey: string,
): Promise<ProviderValidateResponse> {
  return request('/api/providers/validate', {
    method: 'POST',
    body: JSON.stringify({ provider_id: providerId, api_key: apiKey }),
  });
}

export interface RecommendedSource {
  url: string;
  title: string;
  source_type: string;
  relevance_score: number;
}

export async function recommendSources(topic: string): Promise<{ sources: RecommendedSource[] }> {
  return request('/api/recommend-sources', {
    method: 'POST',
    body: JSON.stringify({ topic }),
  });
}

// === 피드백 (F3-06) ===

export async function submitFeedback(
  styleId: string,
  contentId: string,
  rating: 'like' | 'dislike',
  comment?: string,
): Promise<{ ok: boolean; feedback_id: string }> {
  return request('/api/feedback', {
    method: 'POST',
    body: JSON.stringify({ style_id: styleId, content_id: contentId, rating, comment }),
  });
}

// === 팩트체크 (F3-07) ===

export async function factCheck(content: string): Promise<FactCheckResponse> {
  return request('/api/fact-check', {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

// === SEO 최적화 (F3-08) ===

export async function seoOptimize(
  content: string,
  keywords?: string[],
): Promise<SeoOptimizeResponse> {
  return request('/api/seo-optimize', {
    method: 'POST',
    body: JSON.stringify({ content, keywords }),
  });
}

// === 표절 감지 (F3-09) ===

export async function plagiarismCheck(content: string): Promise<PlagiarismResponse> {
  return request('/api/plagiarism-check', {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

// === 가독성 분석 (F3-10) ===

export async function readabilityAnalysis(text: string): Promise<ReadabilityResponse> {
  return request('/api/readability', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

// === 감정 흐름 (F3-11) ===

export async function sentimentFlow(content: string): Promise<SentimentFlowResponse> {
  return request('/api/sentiment-flow', {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
}

// ── NotebookLM ──

export async function notebookLmAuthCheck(): Promise<{ valid: boolean; email?: string; message?: string }> {
  return request('/api/notebooklm/auth-check');
}

export async function notebookLmGenerate(params: {
  type: string;
  url: string;
  source_text: string;
}): Promise<{ artifact_id: string; status: string; content_type: string }> {
  return request('/api/notebooklm/generate', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function notebookLmStatus(artifactId: string): Promise<{ status: string; type?: string; error?: string }> {
  return request(`/api/notebooklm/status/${artifactId}`);
}

// ── Support Assistant / Feedback Handoff ──

export interface SupportViewport {
  width?: number;
  height?: number;
}

export interface SupportTicket {
  id: string;
  kind: 'question' | 'bug' | 'usability' | 'feature' | 'ops' | string;
  status: string;
  severity: 'low' | 'medium' | 'high' | 'critical' | string;
  title: string;
  message: string;
  route?: string;
  viewport?: SupportViewport | null;
  user_agent?: string;
  console_errors?: string[];
  screenshot_url?: string;
  related_files?: string[];
  suggested_fix?: string;
  github_issue_url?: string;
  github_issue_number?: number | null;
  github_pr_url?: string;
  github_pr_number?: number | null;
  labels?: string[];
  created_at: string;
  updated_at: string;
}

export interface SupportChatResponse {
  reply: string;
  action: 'answered' | 'ticket_created' | string;
  ticket?: SupportTicket;
  triage?: Record<string, unknown>;
  github?: { configured: boolean; repo?: string; has_token?: boolean; handoff_enabled?: boolean };
  suggested_next_actions?: string[];
}

export async function supportChat(req: {
  message: string;
  mode?: 'auto' | 'question' | 'feedback' | 'bug' | 'feature';
  route?: string;
  viewport?: SupportViewport;
  user_agent?: string;
  console_errors?: string[];
  screenshot_url?: string;
}): Promise<SupportChatResponse> {
  return request('/api/support/chat', {
    method: 'POST',
    headers: supportHeaders(),
    body: JSON.stringify(req),
  });
}

export async function fetchSupportTickets(): Promise<{ tickets: SupportTicket[]; github?: SupportChatResponse['github'] }> {
  return request('/api/support/tickets', { headers: supportHeaders() });
}

export async function createSupportGithubIssue(ticketId: string): Promise<{ ticket: SupportTicket; issue?: { html_url?: string; number?: number } }> {
  return request(`/api/support/tickets/${ticketId}/create-github-issue`, { method: 'POST', headers: supportHeaders() });
}

export async function createSupportDraftPr(ticketId: string): Promise<{ ticket: SupportTicket; pull_request?: { html_url?: string; number?: number } }> {
  return request(`/api/support/tickets/${ticketId}/create-draft-pr`, { method: 'POST', headers: supportHeaders() });
}

// === 결과 Q&A 채팅 ===

export interface ResultChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ResultChatNote {
  id?: string;
  title?: string;
  score?: number;
  snippet?: string;
}

export interface ResultChatResponse {
  answer: string;
  notes?: ResultChatNote[];
  usage?: { prompt_tokens?: number; completion_tokens?: number; total_tokens?: number };
}

export async function askResultChat(req: {
  question: string;
  context: string;
  history?: ResultChatMessage[];
  model?: string;
  language?: string;
}): Promise<ResultChatResponse> {
  return request('/api/chat', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

// ── 지식 노트 (학습 엔진) ──

export interface NoteSource {
  type: 'youtube' | 'article' | (string & {});
  url: string;
  title: string;
}

export interface NoteListItem {
  id: string;
  title: string;
  tags: string[];
  created_at: string;
  source: NoteSource;
}

export interface NoteQuote {
  text: string;
  ref: string;
}

export interface NoteDetail {
  id: string;
  source: NoteSource;
  key_concepts: string[];
  summary: string;
  quotes: NoteQuote[];
  tags: string[];
  language: string;
  created_at: string;
}

export interface NoteSearchResult {
  id: string;
  title: string;
  score: number;
  snippet: string;
}

export async function getNotes(): Promise<{ notes: NoteListItem[] }> {
  return request('/api/notes');
}

export async function getNote(noteId: string): Promise<NoteDetail> {
  return request(`/api/notes/${encodeURIComponent(noteId)}`);
}

export async function searchNotes(query: string, limit?: number): Promise<{ notes: NoteSearchResult[] }> {
  const params = new URLSearchParams({ q: query });
  if (limit) params.set('limit', String(limit));
  return request(`/api/notes/search?${params}`);
}
