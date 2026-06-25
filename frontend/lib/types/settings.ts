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
  api_base?: string;
  models: ModelInfo[];
  model_count?: number;
  default_model?: string | null;
  health?: ProviderHealth;
  diagnostics?: ProviderDiagnostics;
}

export interface ModelInfo {
  id: string;
  name: string;
  max_input_tokens: number;
  price_input: number;
  price_output: number;
}

export type ProviderHealthStatus = 'ready' | 'missing_key' | 'unavailable' | 'unknown';
export type ProviderHealthSeverity = 'ok' | 'warning' | 'error';

export interface ProviderHealth {
  status: ProviderHealthStatus;
  severity: ProviderHealthSeverity;
  label: string;
  message: string;
  action?: string;
  is_default?: boolean;
  is_selectable?: boolean;
  provider_label?: string;
}

export interface ProviderDiagnostics {
  provider_id: string;
  provider_name?: string;
  provider_label?: string;
  available: boolean;
  generation_visible: boolean;
  api_key_configured: boolean;
  base_url_configured: boolean;
  model_count: number;
  default_model?: string | null;
  health_status?: ProviderHealthStatus;
  health_label?: string;
  safe_summary?: string;
  next_step?: string;
  required_env?: string[];
}

export interface ProviderDiagnosticEntry {
  health: ProviderHealth;
  diagnostics: ProviderDiagnostics;
}

export interface CustomStyle {
  id: string;
  name: string;
  icon: string;
  prompt: string;
  createdAt: number;
}
