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

export type FusionPipelineStepStatus = 'success' | 'warning' | 'error';
export type FusionQualityStatus = 'ok' | 'warning' | 'error' | 'disabled';

export interface FusionPipelineStep {
  name: string;
  status: FusionPipelineStepStatus;
  enabled?: boolean;
  requested_count?: number;
  count?: number;
  failed_count?: number;
  failed_urls?: string[];
  collected_count?: number;
  analyzed_count?: number;
  sources_found?: number;
  has_content?: boolean;
  message?: string;
}

export interface FusionPipelineTrace {
  pipeline: 'fusion' | string;
  model: string;
  steps: FusionPipelineStep[];
  warnings: string[];
}

export interface FusionSourceCoverageSummary {
  status: Exclude<FusionQualityStatus, 'disabled'>;
  requested_count: number;
  collected_count: number;
  summary_count: number;
  failed_count: number;
}

export interface FusionCommentReflectionSummary {
  status: FusionQualityStatus;
  enabled: boolean;
  collected_count: number;
  analyzed_count: number;
  reflected: boolean;
}

export interface FusionWebResearchSummary {
  status: FusionQualityStatus;
  enabled: boolean;
  sources_found: number;
}

export interface FusionFinalGenerationSummary {
  status: Exclude<FusionQualityStatus, 'disabled'>;
  has_content: boolean;
}

export interface FusionQualitySummary {
  status: Exclude<FusionQualityStatus, 'disabled'>;
  source_coverage: FusionSourceCoverageSummary;
  comment_reflection: FusionCommentReflectionSummary;
  web_research: FusionWebResearchSummary;
  final_generation?: FusionFinalGenerationSummary;
  warnings: string[];
}

export interface GenerationSourceQualitySummary {
  status: Exclude<FusionQualityStatus, 'disabled'>;
  type: string;
  has_content: boolean;
  char_count: number;
  transcript_source?: string;
}

export interface GenerationCommentQualitySummary {
  status: FusionQualityStatus;
  available_count: number;
  reflected: boolean;
}

export interface GenerationBodyQualitySummary {
  status: Exclude<FusionQualityStatus, 'disabled'>;
  has_title: boolean;
  has_content: boolean;
  has_html: boolean;
  char_count: number;
}

export interface GenerationQualitySummary {
  kind: 'generation';
  status: Exclude<FusionQualityStatus, 'disabled'>;
  source: GenerationSourceQualitySummary;
  comments: GenerationCommentQualitySummary;
  body: GenerationBodyQualitySummary;
  warnings: string[];
}

export type QualitySummary = FusionQualitySummary | GenerationQualitySummary;

export interface FusionSections {
  faq: string;
  fact_checks: string[];
  sources_used: Array<{ type: string; title: string; url: string }>;
}

export interface Citation {
  marker: string;
  seconds: number;
  context: string;
  valid?: boolean;
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
  merged?: boolean;
  source_videos?: SourceVideo[];
  isFusion?: boolean;
  fusionMeta?: FusionMeta;
  sections?: FusionSections;
  pipelineTrace?: FusionPipelineTrace;
  qualitySummary?: QualitySummary;
  shorts_clips?: ShortsClip[];
  quality_score?: QualityScore;
  analysis?: NlpAnalysis;
  web_sources?: WebSource[];
  inserted_links?: InsertedLink[];
  transcript?: string;
  transcript_segments?: Array<{ start: number; text: string }>;
  chapters?: Array<{ title: string; start: number; end: number; summary: string }>;
  citations?: Citation[];
  favorite?: boolean;
  share_url?: string;
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
