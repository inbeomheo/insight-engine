// === API 요청/응답 타입 ===

export interface GenerateRequest {
  url: string;
  model: string;
  style: string;
  modifiers: Modifiers;
  customPrompt?: string;
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
  youtube_title?: string;
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
  error?: string;
}

// === 결과 보고서 ===

export interface SourceVideo {
  url: string;
  title: string;
  transcript_source: string;
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
  time: string;
  createdAt: number;
  mindmapMarkdown?: string;
  /** 합쳐서 생성 여부 */
  merged?: boolean;
  /** 합쳐서 생성 시 원본 영상 목록 */
  source_videos?: SourceVideo[];
}

// === 설정 ===

export interface Modifiers {
  length: 'short' | 'medium' | 'long';
  writing_style: 'conversational' | 'explanatory' | 'casual' | 'expert';
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
