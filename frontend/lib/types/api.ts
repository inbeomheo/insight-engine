// === API 요청/응답 타입 ===

import type { TokenUsage, SeoMetadata, GeoMetadata, FaqSchema, CtaData, JsonLdSchema, NlpAnalysis, InsertedLink, Citation, WebSource } from './report';
import type { Modifiers, TranscriptLanguage } from './settings';

export interface GenerateRequest {
  url: string;
  model: string;
  style: string;
  modifiers: Modifiers;
  customPrompt?: string;
  /** 직접 텍스트 입력 (URL 대신 사용) */
  content?: string;
  /** Research → Writer → Editor → SEO 멀티에이전트 파이프라인 사용 */
  agent_mode?: boolean;
  /** 생성 깊이: brief | standard | deep */
  detail_level?: 'brief' | 'standard' | 'deep';
  /** 자막 추출 언어 지정 (YouTube 다국어 자막 대상). null/undefined=자동 */
  transcript_language?: TranscriptLanguage;
}

export interface GenerateResponse {
  id?: string;
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
  inserted_links?: InsertedLink[];
  transcript_segments?: Array<{ start: number; text: string }>;
  chapters?: Array<{ title: string; start: number; end: number; summary: string }>;
  citations?: Citation[];
  /** agent_mode 요청이 백그라운드 job으로 전환된 경우 */
  async?: boolean;
  job_id?: string;
  job?: AgentJob;
  status?: string;
}

export interface AgentJobStep {
  id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  error?: string | null;
}

export interface AgentJob {
  id: string;
  type: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
  payload: Record<string, unknown>;
  steps: AgentJobStep[];
  current_step?: string | null;
  failed_step?: string | null;
  result?: {
    final: {
      title: string;
      content: string;
      seo?: SeoMetadata;
      sources?: WebSource[];
    };
    elapsed_seconds?: number;
    agent_count?: number;
  } | null;
  error?: string | null;
}

export interface JobResponse {
  job: AgentJob;
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
  geo?: GeoMetadata;
  faq_schema?: FaqSchema;
  cta?: CtaData;
  error?: string;
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

// === 프로바이더 API 응답 ===

import type { ProviderInfo } from './settings';

export interface ProvidersResponse {
  providers: Record<string, ProviderInfo>;
  style_options: Array<[string, string]>;
}

export interface SharePageResponse {
  id: string;
  share_url: string;
  title: string;
  created_at: string;
}

// === 프로바이더 유효성 검사 ===

export interface ProviderValidateResponse {
  valid: boolean;
  model_tested?: string;
  error?: string;
}

// === 팩트체크 (F3-07) ===

export interface FactClaim {
  claim: string;
  category: 'statistic' | 'date' | 'person' | 'event' | 'technical' | 'other';
  verifiable: boolean;
  confidence: number;
  reasoning: string;
}

export interface FactCheckResponse {
  claims: FactClaim[];
  summary: {
    total: number;
    verified: number;
    uncertain: number;
    suspicious: number;
  };
}

// === SEO 최적화 (F3-08) ===

export interface SeoOptimizeResponse {
  score: number;
  keyword_density: Record<string, { count: number; density_percent: number }>;
  heading_structure: { h2: number; h3: number; h2_texts?: string[] };
  suggestions: string[];
  meta_length: { char_count: number; word_count: number };
}

// === 표절 감지 (F3-09) ===

export interface PlagiarismResponse {
  score: number;
  duplicate_ratio: number;
  repeated_phrases: { phrase: string; count: number }[];
  similar_sentences: { sentence_a: string; sentence_b: string; similarity: number }[];
  verdict: 'clean' | 'minor' | 'significant';
}

// === 가독성 (F3-10) ===

export interface ReadabilityResponse {
  score: number;
  grade: 'A' | 'B' | 'C' | 'D';
  details: {
    avg_sentence_length: number;
    vocabulary_diversity: number;
    foreign_ratio: number;
    paragraph_count: number;
    sentence_count: number;
    char_count: number;
  };
  suggestions: string[];
}

// === 감정 흐름 (F3-11) ===

export interface SentimentFlowItem {
  paragraph_index: number;
  text_preview: string;
  sentiment: 'positive' | 'neutral' | 'negative';
  score: number;
  emotion: string;
}

export interface SentimentFlowResponse {
  flow: SentimentFlowItem[];
  overall_arc: 'ascending' | 'descending' | 'stable' | 'fluctuating';
  dominant_emotion: string;
}

// === 플랫폼 리라이트 ===

export interface RewriteResponse {
  platform: string;
  text: string;
  char_count: number;
  max_chars: number;
}

// === QA 게이트 ===

export interface QaIssue {
  type: string;
  message: string;
  severity: 'error' | 'warning';
  words?: string[];
}

export interface QaCheckResponse {
  passed: boolean;
  issues: QaIssue[];
  score: number;
}
