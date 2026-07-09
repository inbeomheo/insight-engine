import { create } from 'zustand';
import type { Modifiers, ProviderInfo, CustomStyle, GenerationMode, TranscriptLanguage } from '@/lib/types';
import {
  loadSelectedProvider,
  saveSelectedProvider,
  loadSelectedModel,
  saveSelectedModel,
  loadCustomStyles,
  saveCustomStyles,
  loadWebhookUrl,
  saveWebhookUrl,
} from '@/lib/storage';

interface SettingsState {
  // 프로바이더
  providers: Record<string, ProviderInfo>;
  selectedProvider: string;
  selectedModel: string;
  setProviders: (p: Record<string, ProviderInfo>) => void;
  setSelectedProvider: (id: string) => void;
  setSelectedModel: (id: string) => void;

  // 스타일
  selectedStyle: string;
  setSelectedStyle: (id: string) => void;

  // 모디파이어
  modifiers: Modifiers;
  setModifiers: (m: Partial<Modifiers>) => void;

  // 커스텀 스타일
  customStyles: CustomStyle[];
  addCustomStyle: (s: CustomStyle) => void;
  updateCustomStyle: (id: string, s: Partial<CustomStyle>) => void;
  deleteCustomStyle: (id: string) => void;

  // 웹훅
  webhookUrl: string;
  setWebhookUrl: (url: string) => void;

  // 생성 모드 & 퓨전 옵션
  generationMode: GenerationMode;
  enableWebResearch: boolean;
  enableDeepComments: boolean;
  setGenerationMode: (mode: GenerationMode) => void;
  setEnableWebResearch: (v: boolean) => void;
  setEnableDeepComments: (v: boolean) => void;

  // 웹 검색 보강 (Grounded Generation)
  enableWebSearch: boolean;
  setEnableWebSearch: (v: boolean) => void;

  // 상세도 프리셋
  detailLevel: 'brief' | 'standard' | 'deep';
  setDetailLevel: (v: 'brief' | 'standard' | 'deep') => void;

  // 자막 추출 언어 (null=자동)
  transcriptLanguage: TranscriptLanguage;
  setTranscriptLanguage: (v: TranscriptLanguage) => void;

  // 멀티에이전트 파이프라인 모드
  enableAgentMode: boolean;
  setEnableAgentMode: (v: boolean) => void;

  // 초기화
  hydrate: () => void;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  providers: {},
  selectedProvider: '',
  selectedModel: '',
  selectedStyle: 'summary',
  modifiers: { length: 'medium', writing_style: 'conversational', language: 'ko' },
  customStyles: [],
  webhookUrl: '',
  generationMode: 'individual',
  enableWebResearch: true,
  enableDeepComments: true,
  enableWebSearch: false,
  enableAgentMode: false,
  detailLevel: 'standard',
  transcriptLanguage: null,

  setProviders: (p) => set({ providers: p }),

  setSelectedProvider: (id) => {
    saveSelectedProvider(id);
    set({ selectedProvider: id });
  },

  setSelectedModel: (id) => {
    saveSelectedModel(id);
    set({ selectedModel: id });
  },

  setSelectedStyle: (id) => set({ selectedStyle: id }),

  setModifiers: (m) =>
    set((s) => ({ modifiers: { ...s.modifiers, ...m } })),

  addCustomStyle: (style) => {
    const next = [...get().customStyles, style];
    saveCustomStyles(next);
    set({ customStyles: next });
  },

  updateCustomStyle: (id, partial) => {
    const next = get().customStyles.map((s) =>
      s.id === id ? { ...s, ...partial } : s
    );
    saveCustomStyles(next);
    set({ customStyles: next });
  },

  deleteCustomStyle: (id) => {
    const next = get().customStyles.filter((s) => s.id !== id);
    saveCustomStyles(next);
    set({ customStyles: next });
  },

  setWebhookUrl: (url) => {
    saveWebhookUrl(url);
    set({ webhookUrl: url });
  },

  setGenerationMode: (mode) => set({ generationMode: mode }),
  setEnableWebResearch: (v) => set({ enableWebResearch: v }),
  setEnableDeepComments: (v) => set({ enableDeepComments: v }),
  setEnableWebSearch: (v) => set({ enableWebSearch: v }),
  setEnableAgentMode: (v) => set({ enableAgentMode: v }),
  setDetailLevel: (v) => set({ detailLevel: v }),
  setTranscriptLanguage: (v) => set({ transcriptLanguage: v }),

  hydrate: () => {
    set({
      selectedProvider: loadSelectedProvider(),
      selectedModel: loadSelectedModel(),
      customStyles: loadCustomStyles(),
      webhookUrl: loadWebhookUrl(),
    });
  },
}));
