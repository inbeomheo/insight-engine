'use client';

import { memo, useState } from 'react';
import { Plus, Trash2, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { toast } from 'sonner';
import { useSnippets, type Snippet } from '@/hooks/useSnippets';

const CATEGORIES = [
  { id: 'intro', label: '인트로' },
  { id: 'cta', label: 'CTA' },
  { id: 'hashtag', label: '해시태그' },
  { id: 'closing', label: '마무리' },
  { id: 'general', label: '일반' },
];

export const SnippetLibrary = memo(function SnippetLibrary() {
  const { snippets, addSnippet, removeSnippet } = useSnippets();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ category: 'general', label: '', content: '' });
  const [filter, setFilter] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filtered = filter ? snippets.filter((s) => s.category === filter) : snippets;

  const handleAdd = async () => {
    if (!form.content.trim()) {
      toast.error('내용을 입력해주세요.');
      return;
    }
    await addSnippet({ ...form, label: form.label || '제목 없음' });
    setForm({ category: 'general', label: '', content: '' });
    setShowForm(false);
    toast.success('스니펫이 저장되었습니다.');
  };

  const handleCopy = (snippet: Snippet) => {
    navigator.clipboard.writeText(snippet.content);
    setCopiedId(snippet.id);
    setTimeout(() => setCopiedId(null), 1500);
    toast.success('클립보드에 복사되었습니다.');
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">스니펫 라이브러리</h3>
        <Button size="sm" variant="outline" onClick={() => setShowForm((v) => !v)}>
          <Plus className="h-3.5 w-3.5 mr-1" /> 추가
        </Button>
      </div>

      {showForm && (
        <div className="space-y-2 p-3 bg-zinc-50 dark:bg-zinc-800/50 rounded-lg border">
          <Input placeholder="제목" value={form.label} onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))} className="h-8 text-sm" />
          <div className="flex gap-1.5 flex-wrap">
            {CATEGORIES.map((c) => (
              <button key={c.id} onClick={() => setForm((f) => ({ ...f, category: c.id }))}
                aria-label={`${c.label} 카테고리 선택`}
                className={`px-2 py-0.5 rounded text-xs border ${form.category === c.id ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300' : 'border-zinc-200 dark:border-zinc-700'}`}>
                {c.label}
              </button>
            ))}
          </div>
          <Textarea placeholder="스니펫 내용..." value={form.content} onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))} rows={3} className="text-sm" />
          <div className="flex gap-2 justify-end">
            <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>취소</Button>
            <Button size="sm" onClick={handleAdd}>저장</Button>
          </div>
        </div>
      )}

      <div className="flex gap-1.5 flex-wrap">
        <button onClick={() => setFilter(null)} aria-label="전체 카테고리 필터" className={`px-2 py-0.5 rounded text-xs border ${!filter ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30' : 'border-zinc-200 dark:border-zinc-700'}`}>전체</button>
        {CATEGORIES.map((c) => (
          <button key={c.id} onClick={() => setFilter(c.id)} aria-label={`${c.label} 카테고리 필터`} className={`px-2 py-0.5 rounded text-xs border ${filter === c.id ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30' : 'border-zinc-200 dark:border-zinc-700'}`}>
            {c.label}
          </button>
        ))}
      </div>

      <ScrollArea className="h-[300px]">
        {filtered.length === 0 ? (
          <p className="text-sm text-zinc-400 text-center py-8">저장된 스니펫이 없습니다.</p>
        ) : (
          <div className="space-y-2">
            {filtered.map((snippet) => (
              <div key={snippet.id} className="p-2.5 border rounded-lg bg-white dark:bg-zinc-800 group">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-medium truncate">{snippet.label}</span>
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0">{CATEGORIES.find((c) => c.id === snippet.category)?.label || snippet.category}</Badge>
                    </div>
                    <p className="text-xs text-zinc-500 mt-1 line-clamp-2">{snippet.content}</p>
                  </div>
                  <div className="flex gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button size="icon" variant="ghost" className="h-8 w-8" onClick={() => handleCopy(snippet)}>
                      {copiedId === snippet.id ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
                    </Button>
                    <Button size="icon" variant="ghost" className="h-6 w-6 text-red-500" onClick={() => removeSnippet(snippet.id)}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
});

export default SnippetLibrary;
