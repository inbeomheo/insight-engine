// === API 요청/응답 타입 ===

import type { TokenUsage, SeoMetadata, GeoMetadata, FaqSchema, CtaData, JsonLdSchema, NlpAnalysis, InsertedLink, Citation, SourceReceipt, WebSource } from './report';
import type { Modifiers, TranscriptLanguage } from './settings';

export interface GenerateRequest {
  /** URL 입력. 직접 텍스트 생성은 빈 문자열과 content를 함께 보낸다. */
  url: string;
  model: string;
  style: string;
  modifiers: Modifiers;
  customPrompt?: string;
  /** 직접 텍스트 입력 (URL 대신 사용) */
  content?: string;
  /** Research → Writer → Editor → SEO 멀티에이전트 파이프라인 사용 */
  agent_mode?: boolean;
  /** 웹 검색 보강 사용 */
  web_search?: boolean;
  /** 생성 깊이: brief | standard | deep */
  detail_level?: 'brief' | 'standard' | 'deep';
  /** 타임스탬프 인용 링크와 source_receipts 생성 */
  enable_citations?: boolean;
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
  transcript_source?: string;
  prompt: string;
  cached?: boolean;
  comment_summary_included?: boolean;
  seo?: SeoMetadata;
  geo?: GeoMetadata;
  faq_schema?: FaqSchema;
  cta?: CtaData;
  json_ld_schemas?: JsonLdSchema[];
  youtube_title?: string;
  source_type?: 'text' | 'document' | 'voice' | 'article' | string;
  source_title?: string;
  source_meta?: {
    source_type: string;
    chars?: number;
    quality_score?: number;
    is_auto?: boolean;
  };
  transcript?: string;
  web_sources?: WebSource[];
  analysis?: NlpAnalysis;
  inserted_links?: InsertedLink[];
  transcript_segments?: Array<{ start: number; text: string }>;
  chapters?: Array<{ title: string; start: number; end: number; summary: string }>;
  citations?: Citation[];
  source_receipts?: SourceReceipt[];
}

// === 스트리밍 이벤트 ===

export type StreamEventType = 'meta' | 'status' | 'delta' | 'result' | 'token' | 'done' | 'error';

export interface StreamEvent {
  type: StreamEventType;
  id?: string;
  data?: string;
  delta?: string;
  stage?: string;
  title?: string;
  content?: string;
  html?: string;
  youtube_title?: string;
  source_type?: 'text' | 'document' | 'voice' | 'article' | string;
  source_title?: string;
  source_meta?: GenerateResponse['source_meta'];
  transcript?: string;
  transcript_source?: string;
  usage?: TokenUsage;
  elapsed_time?: number;
  prompt?: string;
  prompt_length?: number;
  cached?: boolean;
  comment_summary_included?: boolean;
  seo?: SeoMetadata;
  geo?: GeoMetadata;
  faq_schema?: FaqSchema;
  cta?: CtaData;
  web_sources?: WebSource[];
  transcript_segments?: Array<{ start: number; text: string }>;
  chapters?: Array<{ title: string; start: number; end: number; summary: string }>;
  error?: string;
  message?: string;
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
