// === API 요청/응답 타입 ===

export interface GenerateRequest {
  url: string;
  model: string;
  style: string;
  modifiers: Modifiers;
  customPrompt?: string;
}

export interface WebSource {
  title: string;
  url: string;
  content: string;
  score: number;
}

export interface GenerateResponse {
  title: string;
  content: string;
  html: string;
  usage: TokenUsage;
  elapsed_time: number;
  transcript_source: string;
  prompt: string;
  cached: boolean;
  comment_summary_included: boolean;
  seo?: SeoMetadata;
  geo?: GeoMetadata;
  faq_schema?: FaqSchema;
  cta?: CtaData;
  json_ld_schemas?: JsonLdSchema[];
  youtube_title?: string;
  web_sources?: WebSource[];
  analysis?: NlpAnalysis;
}

export interface TokenUsage {
  total_tokens: number;
  input_tokens?: number;
  output_tokens?: number;
}

export interface SeoMetadata {
  meta_description: string;
  keywords: string[];
  slug: string;
  tags: string[];
}

export interface GeoMetadata {
  citations: string[];         // AI 검색에서 인용 가능한 핵심 팩트
  structured_data: Record<string, string>;  // 구조화된 데이터 (key-value)
  entity_tags: string[];       // 핵심 엔티티/개념 태그
  key_facts: string[];         // 검증 가능한 핵심 사실
}

export interface FaqItem {
  question: string;
  answer: string;
}

export interface FaqSchema {
  '@context': string;
  '@type': string;
  mainEntity: Array<{
    '@type': string;
    name: string;
    acceptedAnswer: { '@type': string; text: string };
  }>;
}

export interface CtaData {
  primary?: string;
  secondary?: string;
}

// JSON-LD 구조화 데이터 스키마 (VideoObject | FAQPage | Article)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type JsonLdSchema = Record<string, any>;

// === 스트리밍 이벤트 ===

export type StreamEventType = 'meta' | 'token' | 'done' | 'error';

export interface StreamEvent {
  type: StreamEventType;
  data?: string;
  title?: string;
  youtube_title?: string;
  transcript_source?: string;
  usage?: TokenUsage;
  elapsed_time?: number;
  prompt?: string;
  cached?: boolean;
  comment_summary_included?: boolean;
  seo?: SeoMetadata;
  geo?: GeoMetadata;
  faq_schema?: FaqSchema;
  cta?: CtaData;
  error?: string;
}

// === 결과 보고서 ===

export interface SourceVideo {
  url: string;
  title: string;
  transcript_source: string;
}

export interface FusionMeta {
  videos_analyzed: number;
  comments_analyzed: number;
  web_sources_found: number;
  total_tokens: number;
  processing_time: number;
  failed_urls: string[];
}

export interface FusionSections {
  faq: string;
  fact_checks: string[];
  sources_used: Array<{ type: string; title: string; url: string }>;
}

export interface Report {
  id: string;
  url: string;
  youtube_title: string;
  title: string;
  content: string;
  html: string;
  style: string;
  prompt: string;
  usage: TokenUsage;
  elapsed_time: number;
  transcript_source: string;
  cached: boolean;
  comment_summary_included: boolean;
  seo?: SeoMetadata;
  geo?: GeoMetadata;
  faq_schema?: FaqSchema;
  cta?: CtaData;
  json_ld_schemas?: JsonLdSchema[];
  time: string;
  createdAt: number;
  mindmapMarkdown?: string;
  /** 합쳐서 생성 여부 */
  merged?: boolean;
  /** 합쳐서 생성 시 원본 영상 목록 */
  source_videos?: SourceVideo[];
  /** 퓨전 분석 여부 */
  isFusion?: boolean;
  /** 퓨전 분석 메타데이터 */
  fusionMeta?: FusionMeta;
  /** 퓨전 분석 섹션 (FAQ, 팩트체크, 소스) */
  sections?: FusionSections;
  /** Shorts 클립 추출 결과 */
  shorts_clips?: ShortsClip[];
  /** 품질 자동 평가 결과 (quality_check: true 요청 시만 포함) */
  quality_score?: QualityScore;
  /** NLP 분석 결과 (analyze: true 요청 시만 포함) */
  analysis?: NlpAnalysis;
  /** 웹 검색 보강 출처 */
  web_sources?: WebSource[];
}

// === Shorts 클립 ===

export interface ShortsClip {
  title: string;
  hook_text: string;
  script: string;
  timestamp_start?: string;
  timestamp_end?: string;
  duration_seconds?: number;
}

// === 생성 모드 ===

export type GenerationMode = 'individual' | 'combined' | 'fusion';

// === 설정 ===

export interface Modifiers {
  length: 'short' | 'medium' | 'long';
  writing_style: 'conversational' | 'explanatory' | 'casual' | 'expert';
  language?: 'ko' | 'en' | 'ja';
}

export interface StyleOption {
  id: string;
  label: string;
  emoji: string;
}

export interface ProviderInfo {
  name: string;
  api_base: string;
  models: ModelInfo[];
}

export interface ModelInfo {
  id: string;
  name: string;
  max_input_tokens: number;
  price_input: number;
  price_output: number;
}

export interface CustomStyle {
  id: string;
  name: string;
  icon: string;
  prompt: string;
  createdAt: number;
}

// === 프로바이더 API 응답 ===

export interface ProvidersResponse {
  providers: Record<string, ProviderInfo>;
  style_options: Array<[string, string]>;
}

// === 마인드맵 ===

export interface MindmapResponse {
  markdown: string;
}

// === 재생목록 ===

export interface PlaylistVideo {
  videoId: string;
  title: string;
  thumbnail: string;
}

export interface PlaylistResponse {
  videos: PlaylistVideo[];
  total: number;
}

// === 멀티 스타일 ===

export interface MultiStyleResponse {
  results: GenerateResponse[];
  youtube_title: string;
  transcript_source: string;
}

// === 파이프라인 ===

export interface PipelineStep {
  id: string;
  name: string;
  description: string;
  progress: number;
  status: 'pending' | 'running' | 'done' | 'error';
  elapsed?: number;
  error?: string;
}

export type PipelineEventType =
  | 'step_start'
  | 'step_complete'
  | 'step_error'
  | 'pipeline_complete';

export interface PipelineEvent {
  type: PipelineEventType;
  step?: string;
  name?: string;
  description?: string;
  progress: number;
  elapsed?: number;
  error?: string;
  result?: GenerateResponse;
}

export interface PipelineRequest {
  pipeline_id: string;
  url: string;
  model: string;
  style: string;
  modifiers: Modifiers;
  customPrompt?: string;
}

// === MCP 플러그인 ===

export interface McpPlugin {
  id: string;
  name: string;
  description: string;
}

export interface McpPublishRequest {
  plugin_id: string;
  title: string;
  content: string;
}

export interface McpPublishResponse {
  success: boolean;
  message: string;
  url?: string;
}

// === 예약 발행 ===

export interface ScheduledPost {
  id: string;
  title: string;
  content: string;
  html?: string;
  target_plugin: string;
  scheduled_at: string;
  status: 'pending' | 'published' | 'failed' | 'cancelled';
  error_message?: string;
  published_url?: string;
  created_at: string;
}

// === 품질 평가 ===

export interface QualityScore {
  accuracy: number;
  coherence: number;
  readability: number;
  usefulness: number;
  overall: number;
  grade: 'A' | 'B' | 'C' | 'D';
  feedback: string;
  eval_model?: string;
}

// === NLP 분석 ===

export interface NlpKeyword {
  word: string;
  relevance: number;
}

export interface NlpAspect {
  aspect: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  score: number;
}

export interface NlpSentiment {
  overall: 'positive' | 'neutral' | 'negative';
  score: number;
  aspects: NlpAspect[];
}

export interface NlpTopic {
  topic: string;
  confidence: number;
}

export interface NlpAnalysis {
  keywords: NlpKeyword[];
  sentiment: NlpSentiment;
  topics: NlpTopic[];
}

// === 지식 베이스 (RAG) ===

export interface KnowledgeItem {
  id: string;
  filename: string;
  uploaded_at: string;
  chunk_count: number;
}

// === 워크스페이스 ===

export type WorkspaceRole = 'owner' | 'editor' | 'viewer';

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  my_role?: WorkspaceRole;
}

export interface WorkspaceMember {
  user_id: string;
  email?: string;
  role: WorkspaceRole;
  joined_at: string;
}
