'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, BookOpen, FileText, Search, Youtube } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { getNotes, searchNotes, type NoteListItem, type NoteSearchResult } from '@/lib/api';

function SourceIcon({ type }: { type: string }) {
  if (type === 'youtube') return <Youtube className="h-4 w-4 text-red-500/80 shrink-0" />;
  return <FileText className="h-4 w-4 text-muted-foreground/70 shrink-0" />;
}

function formatDate(iso: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
}

export default function NotesPage() {
  const [notes, setNotes] = useState<NoteListItem[]>([]);
  const [searchResults, setSearchResults] = useState<NoteSearchResult[] | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getNotes()
      .then((res) => {
        if (!alive) return;
        setNotes(res.notes);
        setError(null);
      })
      .catch((err) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : '노트 목록을 불러오지 못했습니다.');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    setError(null);
    try {
      const res = await searchNotes(q);
      setSearchResults(res.notes);
    } catch (err) {
      setError(err instanceof Error ? err.message : '검색에 실패했습니다.');
    } finally {
      setSearching(false);
    }
  }, [query]);

  const handleClear = useCallback(() => {
    setQuery('');
    setSearchResults(null);
  }, []);

  const isSearchMode = searchResults !== null;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-8">
        {/* 헤더 */}
        <div className="flex items-center gap-3 mb-6">
          <Button asChild variant="ghost" size="icon" className="h-8 w-8 -ml-2">
            <Link href="/" aria-label="홈으로 돌아가기">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-primary/70" />
            <h1 className="text-lg font-semibold text-foreground">노트</h1>
          </div>
        </div>

        {/* 검색 */}
        <form onSubmit={handleSearch} className="flex items-center gap-2 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="노트 검색 (핵심 개념, 요약 내용 등)"
              className="pl-9"
              maxLength={200}
            />
          </div>
          <Button type="submit" disabled={searching || !query.trim()}>
            검색
          </Button>
          {isSearchMode && (
            <Button type="button" variant="ghost" onClick={handleClear}>
              지우기
            </Button>
          )}
        </form>

        {error && (
          <p className="text-sm text-destructive mb-4">{error}</p>
        )}

        {/* 로딩 */}
        {loading ? (
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-20 w-full rounded-lg" />
            ))}
          </div>
        ) : isSearchMode ? (
          <SearchResultsList results={searchResults} />
        ) : (
          <NotesList notes={notes} />
        )}
      </div>
    </div>
  );
}

function NotesList({ notes }: { notes: NoteListItem[] }) {
  if (notes.length === 0) {
    return (
      <div className="text-center py-16">
        <BookOpen className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">
          아직 노트가 없습니다. 영상이나 아티클을 분석하면 핵심 지식이 노트로 자동 정리됩니다.
        </p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {notes.map((note) => (
        <li key={note.id}>
          <Link href={`/notes/${encodeURIComponent(note.id)}`}>
            <Card className="hover:border-primary/40 hover:shadow-sm transition-all cursor-pointer py-4">
              <CardContent className="px-4">
                <div className="flex items-start gap-2.5">
                  <SourceIcon type={note.source?.type ?? ''} />
                  <div className="min-w-0 flex-1">
                    <h2 className="text-sm font-medium text-foreground truncate">
                      {note.title || '제목 없음'}
                    </h2>
                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      <span className="text-xs text-muted-foreground/70">
                        {formatDate(note.created_at)}
                      </span>
                      {note.tags.slice(0, 4).map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-[10px]">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function SearchResultsList({ results }: { results: NoteSearchResult[] }) {
  if (results.length === 0) {
    return (
      <div className="text-center py-16">
        <Search className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">검색 결과가 없습니다.</p>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {results.map((result) => (
        <li key={result.id}>
          <Link href={`/notes/${encodeURIComponent(result.id)}`}>
            <Card className="hover:border-primary/40 hover:shadow-sm transition-all cursor-pointer py-4">
              <CardContent className="px-4">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-sm font-medium text-foreground truncate">
                    {result.title || '제목 없음'}
                  </h2>
                  <Badge variant="outline" className="text-[10px] shrink-0">
                    유사도 {Math.round(result.score * 100)}%
                  </Badge>
                </div>
                {result.snippet && (
                  <p className="text-xs text-muted-foreground/80 mt-1.5 line-clamp-2">
                    {result.snippet}
                  </p>
                )}
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}
