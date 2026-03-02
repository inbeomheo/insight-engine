'use client';

import { useCallback } from 'react';

const STORAGE_KEY = 'insight-engine-modifier-presets';

interface SavedPreset {
  id: string;
  label: string;
  modifiers: { length?: string; writing_style?: string };
}

export function useModifierPresets() {
  const getSavedPresets = useCallback((): SavedPreset[] => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }, []);

  const savePreset = useCallback((preset: SavedPreset) => {
    const current = getSavedPresets();
    const updated = [...current.filter((p) => p.id !== preset.id), preset];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  }, [getSavedPresets]);

  const removePreset = useCallback((id: string) => {
    const current = getSavedPresets();
    localStorage.setItem(STORAGE_KEY, JSON.stringify(current.filter((p) => p.id !== id)));
  }, [getSavedPresets]);

  return { getSavedPresets, savePreset, removePreset };
}
