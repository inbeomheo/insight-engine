// === 파이프라인 ===

import type { GenerateResponse } from './api';
import type { Modifiers } from './settings';
import type { TokenUsage } from './report';

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
  options?: Record<string, unknown>;
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

// === 자막 관련 ===

export type TranscriptSourceType = 'youtube_api' | 'watch_page' | 'supadata' | 'whisper';

export interface TranscriptSourceMeta {
  source_type: TranscriptSourceType;
  quality_score: number;
  is_auto: boolean;
  language: string;
}

export interface TranscriptSentence {
  index: number;
  text: string;
  start_time: number | null;
}

export interface StructuredTranscript {
  sentences: TranscriptSentence[];
  video_id: string;
  source: string;
  source_meta?: TranscriptSourceMeta;
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

export type ContentStatus = 'draft' | 'review' | 'approved' | 'published' | 'rejected';

export interface WorkspaceContent {
  id: string;
  workspace_id: string;
  content_id: string;
  title: string;
  status: ContentStatus;
  author_id: string;
  reviewer_id?: string;
  review_note?: string;
  created_at: string;
  updated_at: string;
}

// === 발행 큐 ===

export interface PublishQueueItem {
  id: string;
  content_id: string;
  title: string;
  plugin_id: string;
  status: 'queued' | 'publishing' | 'success' | 'failed';
  retry_count: number;
  published_url?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

// === 캠페인 팩 ===

export interface CampaignPack {
  id: string;
  name: string;
  description: string;
  styles: string[];
}

export interface CampaignResult {
  pack_id: string;
  pack_name: string;
  results: GenerateResponse[];
  total_usage: TokenUsage;
}

// === 이벤트 추출 ===

export type VideoEventType = 'action_item' | 'key_point' | 'decision' | 'question';

interface BaseVideoEvent {
  type: VideoEventType;
  content: string;
  timestamp: string;
  context: string;
}

export interface ActionItemEvent extends BaseVideoEvent {
  type: 'action_item';
  priority: 'high' | 'medium' | 'low';
}

export interface KeyPointEvent extends BaseVideoEvent {
  type: 'key_point';
  importance: number;
}

export interface DecisionEvent extends BaseVideoEvent {
  type: 'decision';
  stakeholders: string[];
}

export interface QuestionEvent extends BaseVideoEvent {
  type: 'question';
  status: 'open' | 'resolved';
}

export type VideoEvent = ActionItemEvent | KeyPointEvent | DecisionEvent | QuestionEvent;

export interface EventSummary {
  total: number;
  by_type: Record<VideoEventType, number>;
  type_labels: Record<VideoEventType, string>;
  highlights: {
    high_priority_actions: ActionItemEvent[];
    important_key_points: KeyPointEvent[];
    open_questions: QuestionEvent[];
  };
}
