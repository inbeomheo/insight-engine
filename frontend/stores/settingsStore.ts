import { create } from 'zustand';
import type { Modifiers, ProviderInfo, CustomStyle } from '@/lib/types';
import {
  loadSelectedProvider,
  saveSelectedProvider,
  loadSelectedModel,
  saveSelectedModel,
  loadCustomStyles,
  saveCustomStyles,
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

  // 초기화
  hydrate: () => void;
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  providers: {},
  selectedProvider: '',
  selectedModel: '',
  selectedStyle: 'blog_seo',
  modifiers: { length: 'medium', writing_style: 'conversational' },
  customStyles: [],

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

  hydrate: () => {
    set({
      selectedProvider: loadSelectedProvider(),
      selectedModel: loadSelectedModel(),
      customStyles: loadCustomStyles(),
    });
  },
}));
