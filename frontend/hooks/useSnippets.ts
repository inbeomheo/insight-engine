'use client';

import { useState, useCallback, useEffect } from 'react';

const LOCAL_KEY = 'insight-engine-snippets';

export interface Snippet {
  id: string;
  category: string;
  label: string;
  content: string;
  created_at?: string;
}

export function useSnippets() {
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchSnippets = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/user/snippets');
      if (res.ok) {
        const data = await res.json();
        setSnippets(data.snippets || []);
        setLoading(false);
        return;
      }
    } catch { /* Supabase 미연결 → localStorage 폴백 */ }

    // localStorage 폴백
    try {
      const raw = localStorage.getItem(LOCAL_KEY);
      setSnippets(raw ? JSON.parse(raw) : []);
    } catch {
      setSnippets([]);
    }
    setLoading(false);
  }, []);

  const addSnippet = useCallback(async (data: { category: string; label: string; content: string }) => {
    try {
      const res = await fetch('/api/user/snippets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (res.ok) {
        await fetchSnippets();
        return;
      }
    } catch { /* fallback */ }

    // localStorage 폴백
    const newSnippet: Snippet = { id: crypto.randomUUID(), ...data, created_at: new Date().toISOString() };
    setSnippets((prev) => {
      const updated = [newSnippet, ...prev];
      localStorage.setItem(LOCAL_KEY, JSON.stringify(updated));
      return updated;
    });
  }, [fetchSnippets]);

  const removeSnippet = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/user/snippets/${id}`, { method: 'DELETE' });
      if (res.ok) {
        await fetchSnippets();
        return;
      }
    } catch { /* fallback */ }

    setSnippets((prev) => {
      const updated = prev.filter((s) => s.id !== id);
      localStorage.setItem(LOCAL_KEY, JSON.stringify(updated));
      return updated;
    });
  }, [fetchSnippets]);

  useEffect(() => { fetchSnippets(); }, [fetchSnippets]);

  return { snippets, loading, addSnippet, removeSnippet, refresh: fetchSnippets };
}
