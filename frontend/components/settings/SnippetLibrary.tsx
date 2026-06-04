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

const categoryLabel = (id: string) => CATEGORIES.find((category) => category.id === id)?.label || id;

export const SnippetLibrary = memo(function SnippetLibrary() {
  const { snippets, loading, addSnippet, removeSnippet } = useSnippets();
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
    <section
      data-testid="snippet-library"
      role="region"
      aria-labelledby="snippet-library-title"
      aria-describedby="snippet-library-description"
      className="space-y-4 border-t pt-4"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 id="snippet-library-title" data-testid="snippet-library-title" className="text-sm font-semibold">
            스니펫 라이브러리
          </h3>
          <p id="snippet-library-description" data-testid="snippet-library-description" className="mt-1 text-xs text-muted-foreground">
            자주 쓰는 문구를 저장하고 생성 작업 중 빠르게 복사합니다.
          </p>
        </div>
        <Button
          data-testid="snippet-add-toggle"
          size="sm"
          variant="outline"
          aria-expanded={showForm}
          aria-controls="snippet-form"
          aria-label={showForm ? '스니펫 추가 폼 닫기' : '스니펫 추가 폼 열기'}
          onClick={() => setShowForm((v) => !v)}
        >
          <Plus className="mr-1 h-3.5 w-3.5" /> 추가
        </Button>
      </div>

      {showForm && (
        <div
          id="snippet-form"
          data-testid="snippet-form"
          role="form"
          aria-labelledby="snippet-form-title"
          className="space-y-2 rounded-lg border bg-zinc-50 p-3 dark:bg-zinc-800/50"
        >
          <h4 id="snippet-form-title" className="sr-only">
            새 스니펫 추가
          </h4>
          <Input
            data-testid="snippet-title-input"
            aria-label="스니펫 제목"
            placeholder="제목"
            value={form.label}
            onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
            className="h-8 text-sm"
          />
          <div role="radiogroup" aria-label="스니펫 카테고리" className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((category) => (
              <button
                key={category.id}
                type="button"
                aria-label={`${category.label} 카테고리 선택`}
                aria-pressed={form.category === category.id}
                onClick={() => setForm((f) => ({ ...f, category: category.id }))}
                className={`rounded border px-2 py-0.5 text-xs ${
                  form.category === category.id
                    ? 'border-blue-500 bg-blue-50 text-blue-700 dark:bg-blue-950/30 dark:text-blue-300'
                    : 'border-zinc-200 dark:border-zinc-700'
                }`}
              >
                {category.label}
              </button>
            ))}
          </div>
          <Textarea
            data-testid="snippet-content-input"
            aria-label="스니펫 내용"
            placeholder="스니펫 내용..."
            value={form.content}
            onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))}
            rows={3}
            className="text-sm"
          />
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" aria-label="스니펫 추가 취소" onClick={() => setShowForm(false)}>
              취소
            </Button>
            <Button size="sm" aria-label="스니펫 저장" onClick={handleAdd}>
              저장
            </Button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-1.5" role="toolbar" aria-label="스니펫 카테고리 필터">
        <button
          type="button"
          onClick={() => setFilter(null)}
          aria-label="전체 카테고리 필터"
          aria-pressed={!filter}
          className={`rounded border px-2 py-0.5 text-xs ${!filter ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30' : 'border-zinc-200 dark:border-zinc-700'}`}
        >
          전체
        </button>
        {CATEGORIES.map((category) => (
          <button
            key={category.id}
            type="button"
            onClick={() => setFilter(category.id)}
            aria-label={`${category.label} 카테고리 필터`}
            aria-pressed={filter === category.id}
            className={`rounded border px-2 py-0.5 text-xs ${filter === category.id ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30' : 'border-zinc-200 dark:border-zinc-700'}`}
          >
            {category.label}
          </button>
        ))}
      </div>

      <ScrollArea className="h-[260px]">
        {loading ? (
          <p role="status" aria-live="polite" className="py-8 text-center text-sm text-zinc-400">
            스니펫을 불러오는 중...
          </p>
        ) : filtered.length === 0 ? (
          <p role="status" aria-live="polite" className="py-8 text-center text-sm text-zinc-400">
            저장된 스니펫이 없습니다.
          </p>
        ) : (
          <div data-testid="snippet-list" role="list" aria-label="저장된 스니펫" className="space-y-2">
            {filtered.map((snippet) => {
              const helpId = `snippet-actions-help-${snippet.id}`;
              const label = categoryLabel(snippet.category);
              return (
                <article
                  key={snippet.id}
                  data-testid="snippet-item"
                  role="listitem"
                  aria-label={`${snippet.label} 스니펫, ${label} 카테고리`}
                  className="group rounded-lg border bg-white p-2.5 dark:bg-zinc-800"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate text-sm font-medium">{snippet.label}</span>
                        <Badge variant="outline" className="px-1.5 py-0 text-[10px]">
                          {label}
                        </Badge>
                      </div>
                      <p className="mt-1 line-clamp-2 text-xs text-zinc-500">{snippet.content}</p>
                    </div>
                    <p id={helpId} data-testid="snippet-actions-help" className="sr-only">
                      이 스니펫을 클립보드에 복사하거나 라이브러리에서 삭제할 수 있습니다.
                    </p>
                    <div className="flex shrink-0 gap-1 opacity-100 transition-opacity sm:opacity-0 sm:group-hover:opacity-100 sm:focus-within:opacity-100">
                      <Button
                        data-testid="snippet-copy-action"
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8"
                        aria-label={`${snippet.label} 스니펫 복사`}
                        aria-describedby={helpId}
                        onClick={() => handleCopy(snippet)}
                      >
                        {copiedId === snippet.id ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
                      </Button>
                      <Button
                        data-testid="snippet-delete-action"
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-red-500"
                        aria-label={`${snippet.label} 스니펫 삭제`}
                        aria-describedby={helpId}
                        onClick={() => removeSnippet(snippet.id)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </section>
  );
});

export default SnippetLibrary;
