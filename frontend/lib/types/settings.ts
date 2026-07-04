// === 생성 모드 ===

export type GenerationMode = 'individual' | 'combined' | 'fusion';

// === 설정 ===

export interface Modifiers {
  length: 'short' | 'medium' | 'long';
  writing_style: 'conversational' | 'explanatory' | 'casual' | 'expert';
  language?: 'ko' | 'en' | 'ja';
}

/** 자막 추출 언어 — null/undefined=자동(기존 우선순위 폴백) */
export type TranscriptLanguage = 'ko' | 'en' | 'ja' | null;

export interface StyleOption {
  id: string;
  label: string;
  emoji: string;
  description?: string;
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
  size_bytes?: number; // 로컬(Ollama) 모델 디스크 크기 — 동적 조회 시에만 제공
}

export interface CustomStyle {
  id: string;
  name: string;
  icon: string;
  prompt: string;
  createdAt: number;
}
