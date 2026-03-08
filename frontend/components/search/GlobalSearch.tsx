'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Search, FileText, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SearchResult {
  id: string;
  title: string;
  snippet: string;
  style: string;
  score: number;
}

interface GlobalSearchProps {
  onSelect?: (contentId: string) => void;
}

/** 전문 검색 UI (F5-09) */
export default function GlobalSearch({ onSelect }: GlobalSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // 디바운스 검색
  const handleSearch = useCallback((q: string) => {
    setQuery(q);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!q.trim()) {
      setResults([]);
      setTotal(0);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&limit=10`);
        if (res.ok) {
          const data = await res.json();
          setResults(data.results || []);
          setTotal(data.total || 0);
        }
      } catch {
        // 검색 실패 무시
      } finally {
        setLoading(false);
      }
    }, 300);
  }, []);

  // 결과 선택
  const handleSelect = useCallback((id: string) => {
    onSelect?.(id);
    setOpen(false);
    setQuery('');
    setResults([]);
  }, [onSelect]);

  return (
    <div className="relative">
      {/* 검색 입력 */}
      <div className={`flex items-center gap-2 border rounded-lg px-3 py-2 bg-white transition-all ${
        open ? 'border-primary/30 shadow-sm' : 'border-border/60'
      }`}>
        <Search className="h-4 w-4 text-muted-foreground/40 shrink-0" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="콘텐츠 검색..."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/40"
        />
        {query && (
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5"
            onClick={() => { setQuery(''); setResults([]); }}
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>

      {/* 검색 결과 드롭다운 */}
      {open && (query.trim() || results.length > 0) && (
        <>
          {/* 배경 오버레이 */}
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />

          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-border/60
                          rounded-lg shadow-lg z-50 max-h-[400px] overflow-y-auto">
            {loading ? (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground/50">
                검색 중...
              </div>
            ) : results.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground/50">
                {query.trim() ? '검색 결과가 없습니다' : '검색어를 입력하세요'}
              </div>
            ) : (
              <>
                <div className="px-3 py-2 text-[10px] text-muted-foreground/50 border-b border-border/30">
                  {total}건 검색됨
                </div>
                {results.map((r) => (
                  <button
                    key={r.id}
                    className="w-full px-3 py-2.5 text-left hover:bg-accent/50 transition-colors border-b border-border/20 last:border-0"
                    onClick={() => handleSelect(r.id)}
                    aria-label={`${r.title} 검색 결과 선택`}
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
                      <span className="text-sm font-medium truncate">{r.title}</span>
                      {r.style && (
                        <span className="text-[10px] text-muted-foreground/40 bg-muted/50 px-1.5 rounded shrink-0">
                          {r.style}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-muted-foreground/60 mt-1 line-clamp-2 pl-5.5">
                      {r.snippet}
                    </p>
                  </button>
                ))}
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
