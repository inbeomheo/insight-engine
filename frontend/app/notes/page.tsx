'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { ArrowLeft, BookOpen, Brain, FileText, Network, Quote, Search, Tags, Youtube } from 'lucide-react';
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

function topCounts(items: string[], limit: number): Array<{ label: string; count: number }> {
  const counts = new Map<string, number>();
  items
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((item) => counts.set(item, (counts.get(item) ?? 0) + 1));
  return Array.from(counts.entries())
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
    .slice(0, limit);
}

function sourceLabel(type?: string): string {
  if (type === 'youtube') return 'YouTube';
  if (type === 'article') return 'Article';
  return '기타';
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

  const runSearch = useCallback(async (term: string) => {
    const q = term.trim();
    if (!q) {
      setSearchResults(null);
      return;
    }
    setQuery(q);
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
  }, []);

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    void runSearch(query);
  }, [query, runSearch]);

  const handleClear = useCallback(() => {
    setQuery('');
    setSearchResults(null);
  }, []);

  const isSearchMode = searchResults !== null;
  const conceptCount = new Set(notes.flatMap((note) => note.key_concepts ?? [])).size;
  const quoteCount = notes.reduce((sum, note) => sum + (note.quote_count ?? 0), 0);
  const learningPointCount = notes.reduce((sum, note) => sum + (note.learning_point_count ?? 0), 0);
  const topConcepts = useMemo(
    () => topCounts(notes.flatMap((note) => note.key_concepts ?? []), 10),
    [notes],
  );
  const topTags = useMemo(
    () => topCounts(notes.flatMap((note) => note.tags ?? []), 12),
    [notes],
  );
  const sourceGroups = useMemo(
    () => topCounts(notes.map((note) => sourceLabel(note.source?.type)), 4),
    [notes],
  );
  const recentNotes = useMemo(
    () => [...notes]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 3),
    [notes],
  );

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* 헤더 */}
        <div className="mb-6 rounded-2xl border border-border bg-card/60 p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <Button asChild variant="ghost" size="icon" className="h-8 w-8 -ml-2 shrink-0">
                <Link href="/" aria-label="홈으로 돌아가기">
                  <ArrowLeft className="h-4 w-4" />
                </Link>
              </Button>
              <div>
                <div className="flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-primary/70" />
                  <h1 className="text-xl font-semibold text-foreground">LLMWiki 홈</h1>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  학습한 자료가 핵심 개념, 근거 인용, 관련 노트로 쌓이는 지식 베이스입니다.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-5 grid gap-2 sm:grid-cols-4">
            <WikiStat icon={<BookOpen className="h-4 w-4" />} label="노트" value={notes.length} />
            <WikiStat icon={<Brain className="h-4 w-4" />} label="핵심 개념" value={conceptCount} />
            <WikiStat icon={<Quote className="h-4 w-4" />} label="근거 인용" value={quoteCount} />
            <WikiStat icon={<Network className="h-4 w-4" />} label="학습 포인트" value={learningPointCount} />
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

        {!loading && !isSearchMode && notes.length > 0 && (
          <WikiMap
            topConcepts={topConcepts}
            topTags={topTags}
            sourceGroups={sourceGroups}
            recentNotes={recentNotes}
            onSearch={(term) => { void runSearch(term); }}
          />
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

function WikiStat({ icon, label, value }: { icon: ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-xl border border-border bg-background/70 p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="text-primary/70">{icon}</span>
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold text-foreground">{value}</div>
    </div>
  );
}

function WikiMap({
  topConcepts,
  topTags,
  sourceGroups,
  recentNotes,
  onSearch,
}: {
  topConcepts: Array<{ label: string; count: number }>;
  topTags: Array<{ label: string; count: number }>;
  sourceGroups: Array<{ label: string; count: number }>;
  recentNotes: NoteListItem[];
  onSearch: (term: string) => void;
}) {
  return (
    <section className="mb-6 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
      <Card className="py-4">
        <CardContent className="px-4">
          <div className="flex items-center gap-2">
            <Network className="h-4 w-4 text-primary/70" />
            <h2 className="text-sm font-semibold text-foreground">개념 지도</h2>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            반복 등장하는 개념과 태그를 눌러 관련 노트를 바로 이어서 탐색하세요.
          </p>

          {topConcepts.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                핵심 개념
              </div>
              <div className="flex flex-wrap gap-1.5">
                {topConcepts.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => onSearch(item.label)}
                    className="inline-flex items-center gap-1 rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-xs text-primary transition-colors hover:bg-primary/10"
                  >
                    <Brain className="h-3 w-3" />
                    {item.label}
                    <span className="text-[10px] text-primary/60">{item.count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {topTags.length > 0 && (
            <div className="mt-4">
              <div className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                태그
              </div>
              <div className="flex flex-wrap gap-1.5">
                {topTags.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => onSearch(item.label)}
                    className="inline-flex items-center gap-1 rounded-full border border-border bg-background px-2.5 py-1 text-xs text-foreground transition-colors hover:border-primary/40"
                  >
                    <Tags className="h-3 w-3 text-muted-foreground" />
                    {item.label}
                    <span className="text-[10px] text-muted-foreground">{item.count}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-3">
        <Card className="py-4">
          <CardContent className="px-4">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-primary/70" />
              <h2 className="text-sm font-semibold text-foreground">출처 구성</h2>
            </div>
            <div className="mt-3 space-y-2">
              {sourceGroups.map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-lg bg-muted/40 px-3 py-2 text-xs">
                  <span className="text-muted-foreground">{item.label}</span>
                  <span className="font-medium text-foreground">{item.count}개</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="py-4">
          <CardContent className="px-4">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-primary/70" />
              <h2 className="text-sm font-semibold text-foreground">최근 학습 흐름</h2>
            </div>
            <ul className="mt-3 space-y-2">
              {recentNotes.map((note) => (
                <li key={note.id}>
                  <Link
                    href={`/notes/${encodeURIComponent(note.id)}`}
                    className="block rounded-lg border border-border px-3 py-2 transition-colors hover:border-primary/40"
                  >
                    <p className="truncate text-xs font-medium text-foreground">{note.title || '제목 없음'}</p>
                    <p className="mt-0.5 text-[10px] text-muted-foreground">{formatDate(note.created_at)}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </section>
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
    <ul className="grid gap-3 md:grid-cols-2">
      {notes.map((note) => (
        <li key={note.id}>
          <Link href={`/notes/${encodeURIComponent(note.id)}`}>
            <Card className="h-full hover:border-primary/40 hover:shadow-sm transition-all cursor-pointer py-4">
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
                    {note.summary && (
                      <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                        {note.summary}
                      </p>
                    )}
                    {(note.key_concepts?.length ?? 0) > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {note.key_concepts?.slice(0, 5).map((concept) => (
                          <Badge key={concept} variant="outline" className="text-[10px]">
                            <Brain className="mr-1 h-3 w-3" />
                            {concept}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <div className="mt-3 flex items-center gap-3 text-[10px] text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Quote className="h-3 w-3" />
                        인용 {note.quote_count ?? 0}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Network className="h-3 w-3" />
                        포인트 {note.learning_point_count ?? 0}
                      </span>
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
                <p className="mt-2 inline-flex items-center gap-1 text-[10px] text-muted-foreground">
                  <Tags className="h-3 w-3" />
                  이 노트를 열어 관련 개념과 근거를 이어서 확인하세요.
                </p>
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}
