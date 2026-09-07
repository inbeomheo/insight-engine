// === 결과 보고서 + 관련 타입 ===

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
  citations: string[];
  structured_data: Record<string, string>;
  entity_tags: string[];
  key_facts: string[];
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type JsonLdSchema = Record<string, any>;

export interface WebSource {
  title: string;
  url: string;
  content: string;
  score: number;
}

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

export interface Citation {
  marker: string;
  seconds: number;
  context: string;
  valid?: boolean | null;
}

export interface SourceReceipt {
  claim: string;
  marker: string;
  seconds: number;
  timestamp_url: string;
  collected_at: string;
  valid?: boolean | null;
  source: {
    type: 'youtube';
    video_id: string;
    title?: string;
  };
}

export interface ShortsClip {
  title: string;
  hook_text: string;
  script: string;
  timestamp_start?: string;
  timestamp_end?: string;
  duration_seconds?: number;
}

export interface InsertedLink {
  title: string;
  url: string;
  anchor_text?: string;
  type: 'internal' | 'external';
  domain?: string;
}

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

export interface Report {
  id: string;
  /**
   * 현재 SSE 스트림이 이 임시 보고서를 갱신 중인지 여부.
   * 기존 localStorage 보고서에는 없을 수 있으며, 없으면 false로 해석한다.
   */
  is_streaming?: boolean;
  url: string;
  youtube_title: string;
  source_type?: 'text' | 'document' | 'voice' | 'article' | string;
  source_title?: string;
  source_meta?: {
    source_type: string;
    chars?: number;
    quality_score?: number;
    is_auto?: boolean;
  };
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
  merged?: boolean;
  source_videos?: SourceVideo[];
  isFusion?: boolean;
  fusionMeta?: FusionMeta;
  sections?: FusionSections;
  shorts_clips?: ShortsClip[];
  quality_score?: QualityScore;
  analysis?: NlpAnalysis;
  web_sources?: WebSource[];
  inserted_links?: InsertedLink[];
  transcript?: string;
  transcript_segments?: Array<{ start: number; text: string }>;
  chapters?: Array<{ title: string; start: number; end: number; summary: string }>;
  citations?: Citation[];
  source_receipts?: SourceReceipt[];
  favorite?: boolean;
  share_url?: string;
  knowledge_note_id?: string;
  knowledge_note_title?: string;
  knowledge_note_saved_at?: string;
  notebooklm?: NotebookLmData;
}

export interface NotebookLmArtifact {
  artifact_id: string;
  content_type: string;
  status: 'in_progress' | 'completed' | 'failed';
  error?: string;
}

export interface NotebookLmData {
  artifacts: NotebookLmArtifact[];
}

export type ViewMode = 'compact' | 'full' | 'timeline';
