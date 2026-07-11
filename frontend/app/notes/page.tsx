'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, BookOpen, Brain, CalendarClock, CheckCircle2, ChevronDown, Copy, FileText, Flame, MessageSquare, Network, Quote, Search, Tags, X, Youtube } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { getNotes, searchNotes, type NoteListItem, type NoteSearchResult } from '@/lib/api';
import {
  filterNotesByFacet,
  filterNotesByStudyStatus,
  buildDailyStudyPlanMarkdown,
  buildWikiIndexMarkdown,
  getCompletedStudyItems,
  getDailyStudyPlanItems,
  getFacetLabel,
  getKnowledgeGapConcepts,
  getNoteConceptClusters,
  getNoteReviewQueue,
  getNoteSearchResultPresentations,
  getNoteStudyCardOrder,
  getNoteStudyQueueCount,
  getNotesNeedingReview,
  getNoteSourceLabel,
  getNoteStudyCounts,
  getNoteStudyStatus,
  getNoteStudyStatusCounts,
  getNoteStudyStatusLabel,
  getRecentStudyResumeItems,
  getStudyStartCandidates,
  NOTE_STUDY_QUEUE_OPEN_STORAGE_KEY,
  NOTE_WIKI_EXPLORE_OPEN_STORAGE_KEY,
  parseNotePanelOpen,
  parseNoteStudyQueueOpen,
  serializeNotePanelOpen,
  serializeNoteStudyQueueOpen,
  sortNotesByRecent,
  type NoteStudyStatus,
  type NoteStudyResumeItem,
  type NoteStudyPlanItem,
  type NoteStudyCardKind,
  type NoteFacet,
  type NoteConceptCluster,
  type NoteScheduledReviewItem,
  type NoteKnowledgeGap,
  type NoteRecallReinforcementPath,
  buildNoteFacetHref,
  parseNoteFacetSearchParams,
} from '@/lib/note-list';
import { buildNoteRecallSupportHref } from '@/lib/note-recall-flow';
import { readNoteStudyProgress, type NoteStudyProgress } from '@/lib/note-study-progress';
import { readNoteReviewSchedule, type NoteReviewSchedule } from '@/lib/note-review-schedule';
import {
  buildNoteReviewHistoryMarkdown,
  getNoteReviewActivityDays,
  getNoteReviewHistorySummary,
  readNoteReviewHistory,
  type NoteReviewActivityDay,
  type NoteReviewHistoryEntry,
  type NoteReviewHistorySummary,
} from '@/lib/note-review-history';
import {
  buildResultChatStudyCardsMarkdown,
  readResultChatStudyCards,
  type ResultChatStudyCard,
} from '@/lib/result-chat-study-card';

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

function formatStudyUpdatedAt(iso: string | null): string {
  if (!iso) return '기록 없음';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '기록 없음';
  return d.toLocaleString('ko-KR', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
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

export default function NotesPage() {
  const router = useRouter();
  const [notes, setNotes] = useState<NoteListItem[]>([]);
  const [searchResults, setSearchResults] = useState<NoteSearchResult[] | null>(null);
  const [studyProgressByNote, setStudyProgressByNote] = useState<Record<string, NoteStudyProgress>>({});
  const [qnaStudyCards, setQnaStudyCards] = useState<ResultChatStudyCard[]>([]);
  const [reviewScheduleByNote, setReviewScheduleByNote] = useState<Record<string, NoteReviewSchedule | null>>({});
  const [reviewHistory, setReviewHistory] = useState<NoteReviewHistoryEntry[]>([]);
  const [reviewNow, setReviewNow] = useState(() => new Date());
  const [query, setQuery] = useState('');
  const [activeFacet, setActiveFacet] = useState<NoteFacet | null>(null);
  const [activeStudyStatus, setActiveStudyStatus] = useState<NoteStudyStatus | null>(null);
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

  useEffect(() => {
    const syncQnaStudyCards = () => {
      try {
        setQnaStudyCards(readResultChatStudyCards(window.localStorage).slice(0, 3));
      } catch {
        setQnaStudyCards([]);
      }
    };

    syncQnaStudyCards();
    window.addEventListener('storage', syncQnaStudyCards);
    window.addEventListener('focus', syncQnaStudyCards);
    return () => {
      window.removeEventListener('storage', syncQnaStudyCards);
      window.removeEventListener('focus', syncQnaStudyCards);
    };
  }, []);

  useEffect(() => {
    const syncFacetFromUrl = () => {
      const facet = parseNoteFacetSearchParams(new URLSearchParams(window.location.search));
      setActiveFacet(facet);
      if (facet) {
        setSearchResults(null);
        setActiveStudyStatus(null);
      }
    };

    syncFacetFromUrl();
    window.addEventListener('popstate', syncFacetFromUrl);
    return () => window.removeEventListener('popstate', syncFacetFromUrl);
  }, []);

  const runSearch = useCallback(async (term: string) => {
    const q = term.trim();
    if (!q) {
      setSearchResults(null);
      return;
    }
    setQuery(q);
    setActiveFacet(null);
    setActiveStudyStatus(null);
    router.replace('/notes', { scroll: false });
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
  }, [router]);

  useEffect(() => {
    if (notes.length === 0) {
      setStudyProgressByNote({});
      return;
    }
    setStudyProgressByNote(
      Object.fromEntries(
        notes.map((note) => [
          note.id,
          readNoteStudyProgress(note.id, getNoteStudyCounts(note)),
        ])
      )
    );
  }, [notes]);

  useEffect(() => {
    const syncReviewSchedules = () => {
      setReviewScheduleByNote(
        Object.fromEntries(notes.map((note) => [note.id, readNoteReviewSchedule(note.id)]))
      );
    };

    syncReviewSchedules();
    window.addEventListener('storage', syncReviewSchedules);
    window.addEventListener('focus', syncReviewSchedules);
    return () => {
      window.removeEventListener('storage', syncReviewSchedules);
      window.removeEventListener('focus', syncReviewSchedules);
    };
  }, [notes]);

  useEffect(() => {
    const syncReviewHistory = () => setReviewHistory(readNoteReviewHistory());
    syncReviewHistory();
    window.addEventListener('storage', syncReviewHistory);
    window.addEventListener('focus', syncReviewHistory);
    return () => {
      window.removeEventListener('storage', syncReviewHistory);
      window.removeEventListener('focus', syncReviewHistory);
    };
  }, []);

  useEffect(() => {
    const intervalId = window.setInterval(() => setReviewNow(new Date()), 60_000);
    return () => window.clearInterval(intervalId);
  }, []);

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    void runSearch(query);
  }, [query, runSearch]);

  const handleClear = useCallback(() => {
    setQuery('');
    setSearchResults(null);
    router.replace('/notes', { scroll: false });
  }, [router]);

  const handleFacetSelect = useCallback((facet: NoteFacet) => {
    setSearchResults(null);
    setActiveFacet(facet);
    setActiveStudyStatus(null);
    router.replace(buildNoteFacetHref(facet), { scroll: false });
  }, [router]);

  const handleFacetClear = useCallback(() => {
    setActiveFacet(null);
    router.replace('/notes', { scroll: false });
  }, [router]);

  const handleStudyStatusSelect = useCallback((status: NoteStudyStatus) => {
    setSearchResults(null);
    setActiveFacet(null);
    setActiveStudyStatus((current) => current === status ? null : status);
    router.replace('/notes', { scroll: false });
  }, [router]);

  const isSearchMode = searchResults !== null;
  const conceptCount = new Set(notes.flatMap((note) => note.key_concepts ?? [])).size;
  const quoteCount = notes.reduce((sum, note) => sum + (note.quote_count ?? 0), 0);
  const learningPointCount = notes.reduce((sum, note) => sum + (note.learning_point_count ?? 0), 0);
  const reviewQuestionCount = notes.reduce((sum, note) => sum + (note.review_question_count ?? 0), 0);
  const topConcepts = useMemo(
    () => topCounts(notes.flatMap((note) => note.key_concepts ?? []), 10),
    [notes],
  );
  const topTags = useMemo(
    () => topCounts(notes.flatMap((note) => note.tags ?? []), 12),
    [notes],
  );
  const sourceGroups = useMemo(
    () => topCounts(notes.map((note) => getNoteSourceLabel(note.source?.type)), 4),
    [notes],
  );
  const conceptClusters = useMemo(
    () => getNoteConceptClusters(notes, { limit: 4, notesPerCluster: 3 }),
    [notes],
  );
  const knowledgeGaps = useMemo(
    () => getKnowledgeGapConcepts(notes, 6),
    [notes],
  );
  const recentNotes = useMemo(
    () => [...notes]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 3),
    [notes],
  );
  const visibleNotes = useMemo(
    () => sortNotesByRecent(
      filterNotesByStudyStatus(
        filterNotesByFacet(notes, activeFacet),
        studyProgressByNote,
        activeStudyStatus
      )
    ),
    [notes, activeFacet, activeStudyStatus, studyProgressByNote],
  );
  const reviewNeededNotes = useMemo(
    () => getNotesNeedingReview(notes, studyProgressByNote, 3),
    [notes, studyProgressByNote],
  );
  const studyStartNotes = useMemo(
    () => getStudyStartCandidates(notes, studyProgressByNote, 3),
    [notes, studyProgressByNote],
  );
  const reviewQueue = useMemo(
    () => getNoteReviewQueue(notes, reviewScheduleByNote, reviewHistory, reviewNow, 4),
    [notes, reviewHistory, reviewNow, reviewScheduleByNote],
  );
  const { recallReinforcementPath, scheduledReviewItems } = reviewQueue;
  const reviewHistorySummary = useMemo(
    () => getNoteReviewHistorySummary(reviewHistory),
    [reviewHistory],
  );
  const reviewActivityDays = useMemo(
    () => getNoteReviewActivityDays(reviewHistory),
    [reviewHistory],
  );
  const linkedReviewHistory = useMemo(() => {
    const noteIds = new Set(notes.map((note) => note.id));
    return reviewHistory.filter((entry) => noteIds.has(entry.noteId));
  }, [notes, reviewHistory]);
  const recentReviewHistory = useMemo(() => linkedReviewHistory.slice(0, 3), [linkedReviewHistory]);
  const scheduledReviewNoteIds = useMemo(
    () => new Set([
      ...scheduledReviewItems.map((item) => item.note.id),
      ...(recallReinforcementPath ? [recallReinforcementPath.originalNote.id] : []),
    ]),
    [recallReinforcementPath, scheduledReviewItems],
  );
  const completedStudyNotes = useMemo(
    () => getCompletedStudyItems(notes, studyProgressByNote, notes.length)
      .filter((item) => !scheduledReviewNoteIds.has(item.note.id))
      .slice(0, 3),
    [notes, scheduledReviewNoteIds, studyProgressByNote],
  );
  const studyResumeNotes = useMemo(
    () => getRecentStudyResumeItems(
      notes,
      studyProgressByNote,
      new Set([
        ...reviewNeededNotes.map((item) => item.note.id),
        ...completedStudyNotes.map((item) => item.note.id),
        ...scheduledReviewNoteIds,
      ]),
      3
    ),
    [notes, studyProgressByNote, reviewNeededNotes, completedStudyNotes, scheduledReviewNoteIds],
  );
  const dailyStudyPlanItems = useMemo(
    () => getDailyStudyPlanItems(notes, studyProgressByNote, 3),
    [notes, studyProgressByNote],
  );
  const studyCardOrder = useMemo(
    () => getNoteStudyCardOrder({
      'review-needed': reviewNeededNotes.length,
      'study-start': studyStartNotes.length,
      completed: completedStudyNotes.length,
      recent: studyResumeNotes.length,
    }),
    [completedStudyNotes.length, reviewNeededNotes.length, studyResumeNotes.length, studyStartNotes.length],
  );
  const studyStatusCounts = useMemo(
    () => getNoteStudyStatusCounts(notes, studyProgressByNote),
    [notes, studyProgressByNote],
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
            <WikiStat icon={<Network className="h-4 w-4" />} label="학습 항목" value={learningPointCount + reviewQuestionCount} />
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
            conceptClusters={conceptClusters}
            recallReinforcementPath={recallReinforcementPath}
            knowledgeGaps={knowledgeGaps}
            recentNotes={recentNotes}
            studyStartNotes={studyStartNotes}
            reviewNeededNotes={reviewNeededNotes}
            completedStudyNotes={completedStudyNotes}
            studyResumeNotes={studyResumeNotes}
            dailyStudyPlanItems={dailyStudyPlanItems}
            qnaStudyCards={qnaStudyCards}
            scheduledReviewItems={scheduledReviewItems}
            reviewQueueTotalCount={reviewQueue.totalCount}
            dueReviewCount={reviewQueue.dueCount}
            reviewHistorySummary={reviewHistorySummary}
            reviewActivityDays={reviewActivityDays}
            reviewHistoryEntries={linkedReviewHistory}
            recentReviewHistory={recentReviewHistory}
            studyCardOrder={studyCardOrder}
            onFacetSelect={handleFacetSelect}
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
          <SearchResultsList results={searchResults} notes={notes} />
        ) : (
          <>
            {notes.length > 0 && (
              <StudyStatusFilter
                counts={studyStatusCounts}
                activeStatus={activeStudyStatus}
                resultCount={visibleNotes.length}
                onSelect={handleStudyStatusSelect}
              />
            )}
            {activeFacet && (
              <ActiveFacetBar
                facet={activeFacet}
                resultCount={visibleNotes.length}
                totalCount={notes.length}
                onClear={handleFacetClear}
              />
            )}
            <NotesList
              notes={visibleNotes}
              studyProgressByNote={studyProgressByNote}
              emptyText={(activeFacet || activeStudyStatus) ? '선택한 필터에 맞는 노트가 없습니다.' : undefined}
            />
          </>
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

function StudyStatusFilter({
  counts,
  activeStatus,
  resultCount,
  onSelect,
}: {
  counts: Record<NoteStudyStatus, number>;
  activeStatus: NoteStudyStatus | null;
  resultCount: number;
  onSelect: (status: NoteStudyStatus) => void;
}) {
  const items: Array<{ status: NoteStudyStatus; description: string }> = [
    { status: 'in-progress', description: '체크한 항목이 남은 노트' },
    { status: 'completed', description: '모든 항목을 끝낸 노트' },
    { status: 'not-started', description: '아직 체크하지 않은 노트' },
  ];

  return (
    <div className="mb-4 rounded-xl border border-border bg-card/60 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <CheckCircle2 className="h-4 w-4 text-primary/70" />
          학습 상태
        </div>
        {activeStatus && (
          <span className="text-[10px] text-muted-foreground">
            {getNoteStudyStatusLabel(activeStatus)} {resultCount}개 표시
          </span>
        )}
      </div>
      <div className="grid gap-2 sm:grid-cols-3">
        {items.map((item) => {
          const selected = activeStatus === item.status;
          return (
            <button
              key={item.status}
              type="button"
              onClick={() => onSelect(item.status)}
              aria-pressed={selected}
              className={`rounded-lg border px-3 py-2 text-left transition-colors ${
                selected
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-background text-foreground hover:border-primary/40'
              }`}
            >
              <div className="flex items-center justify-between gap-2 text-xs font-semibold">
                <span>{getNoteStudyStatusLabel(item.status)}</span>
                <span>{counts[item.status]}</span>
              </div>
              <p className="mt-1 text-[10px] text-muted-foreground">{item.description}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ActiveFacetBar({
  facet,
  resultCount,
  totalCount,
  onClear,
}: {
  facet: NoteFacet;
  resultCount: number;
  totalCount: number;
  onClear: () => void;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/20 bg-primary/5 px-3 py-2">
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold text-primary">{getFacetLabel(facet)}</span>
        <span className="text-xs text-muted-foreground">
          {resultCount}/{totalCount}개 노트
        </span>
      </div>
      <Button type="button" size="sm" variant="ghost" className="h-7 gap-1 text-xs" onClick={onClear}>
        <X className="h-3.5 w-3.5" />
        필터 해제
      </Button>
    </div>
  );
}

function WikiMap({
  topConcepts,
  topTags,
  sourceGroups,
  conceptClusters,
  recallReinforcementPath,
  knowledgeGaps,
  recentNotes,
  studyStartNotes,
  reviewNeededNotes,
  completedStudyNotes,
  studyResumeNotes,
  dailyStudyPlanItems,
  qnaStudyCards,
  scheduledReviewItems,
  reviewQueueTotalCount,
  dueReviewCount,
  reviewHistorySummary,
  reviewActivityDays,
  reviewHistoryEntries,
  recentReviewHistory,
  studyCardOrder,
  onFacetSelect,
}: {
  topConcepts: Array<{ label: string; count: number }>;
  topTags: Array<{ label: string; count: number }>;
  sourceGroups: Array<{ label: string; count: number }>;
  conceptClusters: NoteConceptCluster[];
  recallReinforcementPath: NoteRecallReinforcementPath | null;
  knowledgeGaps: NoteKnowledgeGap[];
  recentNotes: NoteListItem[];
  studyStartNotes: NoteStudyResumeItem[];
  reviewNeededNotes: NoteStudyResumeItem[];
  completedStudyNotes: NoteStudyResumeItem[];
  studyResumeNotes: NoteStudyResumeItem[];
  dailyStudyPlanItems: NoteStudyPlanItem[];
  qnaStudyCards: ResultChatStudyCard[];
  scheduledReviewItems: NoteScheduledReviewItem[];
  reviewQueueTotalCount: number;
  dueReviewCount: number;
  reviewHistorySummary: NoteReviewHistorySummary;
  reviewActivityDays: NoteReviewActivityDay[];
  reviewHistoryEntries: NoteReviewHistoryEntry[];
  recentReviewHistory: NoteReviewHistoryEntry[];
  studyCardOrder: NoteStudyCardKind[];
  onFacetSelect: (facet: NoteFacet) => void;
}) {
  const [studyQueueOpen, setStudyQueueOpen] = useState(true);
  const [wikiExploreOpen, setWikiExploreOpen] = useState(true);
  const [studyPlanCopyStatus, setStudyPlanCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const [wikiIndexCopyStatus, setWikiIndexCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const [qnaCardsCopyStatus, setQnaCardsCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const [reviewHistoryCopyStatus, setReviewHistoryCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const [qnaCardCopyStatus, setQnaCardCopyStatus] = useState<{
    id: string;
    status: 'copied' | 'error';
  } | null>(null);
  useEffect(() => {
    try {
      // 브라우저 저장값은 hydration 이후에만 반영합니다.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setStudyQueueOpen(
        parseNoteStudyQueueOpen(window.localStorage.getItem(NOTE_STUDY_QUEUE_OPEN_STORAGE_KEY), true),
      );
    } catch {
      setStudyQueueOpen(true);
    }
  }, []);

  useEffect(() => {
    try {
      // 브라우저 저장값은 hydration 이후에만 반영합니다.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setWikiExploreOpen(
        parseNotePanelOpen(window.localStorage.getItem(NOTE_WIKI_EXPLORE_OPEN_STORAGE_KEY), true),
      );
    } catch {
      setWikiExploreOpen(true);
    }
  }, []);

  const handleStudyQueueToggle = useCallback(() => {
    setStudyQueueOpen((open) => {
      const next = !open;
      try {
        window.localStorage.setItem(
          NOTE_STUDY_QUEUE_OPEN_STORAGE_KEY,
          serializeNoteStudyQueueOpen(next),
        );
      } catch {
        // Ignore unavailable storage; the visible toggle still works.
      }
      return next;
    });
  }, []);

  const handleWikiExploreToggle = useCallback(() => {
    setWikiExploreOpen((open) => {
      const next = !open;
      try {
        window.localStorage.setItem(
          NOTE_WIKI_EXPLORE_OPEN_STORAGE_KEY,
          serializeNotePanelOpen(next),
        );
      } catch {
        // Ignore unavailable storage; the visible toggle still works.
      }
      return next;
    });
  }, []);

  const copyDailyStudyPlan = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.clipboard) {
      setStudyPlanCopyStatus('error');
      return;
    }

    try {
      await navigator.clipboard.writeText(buildDailyStudyPlanMarkdown(dailyStudyPlanItems));
      setStudyPlanCopyStatus('copied');
    } catch {
      setStudyPlanCopyStatus('error');
    }
  }, [dailyStudyPlanItems]);

  useEffect(() => {
    if (studyPlanCopyStatus === 'idle') return;
    const timer = window.setTimeout(() => setStudyPlanCopyStatus('idle'), 2000);
    return () => window.clearTimeout(timer);
  }, [studyPlanCopyStatus]);

  const copyWikiIndex = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.clipboard) {
      setWikiIndexCopyStatus('error');
      return;
    }

    try {
      await navigator.clipboard.writeText(buildWikiIndexMarkdown(conceptClusters));
      setWikiIndexCopyStatus('copied');
    } catch {
      setWikiIndexCopyStatus('error');
    }
  }, [conceptClusters]);

  useEffect(() => {
    if (wikiIndexCopyStatus === 'idle') return;
    const timer = window.setTimeout(() => setWikiIndexCopyStatus('idle'), 2000);
    return () => window.clearTimeout(timer);
  }, [wikiIndexCopyStatus]);

  const copyReviewHistory = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.clipboard) {
      setReviewHistoryCopyStatus('error');
      return;
    }

    try {
      await navigator.clipboard.writeText(buildNoteReviewHistoryMarkdown(reviewHistoryEntries));
      setReviewHistoryCopyStatus('copied');
    } catch {
      setReviewHistoryCopyStatus('error');
    }
  }, [reviewHistoryEntries]);

  useEffect(() => {
    if (reviewHistoryCopyStatus === 'idle') return;
    const timer = window.setTimeout(() => setReviewHistoryCopyStatus('idle'), 2000);
    return () => window.clearTimeout(timer);
  }, [reviewHistoryCopyStatus]);

  const copyQnaStudyCards = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.clipboard) {
      setQnaCardsCopyStatus('error');
      return;
    }

    try {
      await navigator.clipboard.writeText(buildResultChatStudyCardsMarkdown(qnaStudyCards));
      setQnaCardsCopyStatus('copied');
    } catch {
      setQnaCardsCopyStatus('error');
    }
  }, [qnaStudyCards]);

  useEffect(() => {
    if (qnaCardsCopyStatus === 'idle') return;
    const timer = window.setTimeout(() => setQnaCardsCopyStatus('idle'), 2000);
    return () => window.clearTimeout(timer);
  }, [qnaCardsCopyStatus]);

  const copyQnaStudyCard = useCallback(async (card: ResultChatStudyCard) => {
    if (typeof navigator === 'undefined' || !navigator.clipboard) {
      setQnaCardCopyStatus({ id: card.id, status: 'error' });
      return;
    }

    try {
      await navigator.clipboard.writeText(card.markdown);
      setQnaCardCopyStatus({ id: card.id, status: 'copied' });
    } catch {
      setQnaCardCopyStatus({ id: card.id, status: 'error' });
    }
  }, []);

  useEffect(() => {
    if (!qnaCardCopyStatus) return;
    const timer = window.setTimeout(() => setQnaCardCopyStatus(null), 2000);
    return () => window.clearTimeout(timer);
  }, [qnaCardCopyStatus]);

  const studyQueueCounts = {
    'review-needed': reviewNeededNotes.length,
    'study-start': studyStartNotes.length,
    completed: completedStudyNotes.length,
    recent: studyResumeNotes.length,
  };
  const totalStudyQueueItems = getNoteStudyQueueCount(studyQueueCounts)
    + qnaStudyCards.length
    + reviewQueueTotalCount;
  const maxReviewActivityCount = Math.max(1, ...reviewActivityDays.map((day) => day.count));
  const totalWikiExploreItems = topConcepts.length + topTags.length + sourceGroups.length + conceptClusters.length + knowledgeGaps.length;
  const studyCardOrderStyle = (kind: NoteStudyCardKind) => {
    const index = studyCardOrder.indexOf(kind);
    return { order: index >= 0 ? index + 1 : 99 };
  };

  return (
    <section className="mb-6 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
      <Card className="py-4">
        <CardContent className="px-4">
          <button
            type="button"
            onClick={handleWikiExploreToggle}
            aria-expanded={wikiExploreOpen}
            className="flex w-full items-center justify-between gap-3 text-left"
          >
            <span>
              <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Network className="h-4 w-4 text-primary/70" />
                지식 탐색
              </span>
              <span className="mt-1 block text-xs text-muted-foreground">
                개념·태그·출처 필터를 필요할 때만 펼칩니다.
              </span>
            </span>
            <span className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
              {totalWikiExploreItems}개 단서
              <ChevronDown className={`h-4 w-4 transition-transform ${wikiExploreOpen ? 'rotate-180' : ''}`} />
            </span>
          </button>

          {wikiExploreOpen && (
            <>
              <p className="mt-3 text-xs text-muted-foreground">
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
                        onClick={() => onFacetSelect({ type: 'concept', value: item.label })}
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
                        onClick={() => onFacetSelect({ type: 'tag', value: item.label })}
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

              {conceptClusters.length > 0 && (
                <div className="mt-4 rounded-xl border border-border bg-background/70 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                      <BookOpen className="h-3.5 w-3.5 text-primary/70" />
                      위키 인덱스
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-muted-foreground">
                          개념별 문서 묶음
                        </span>
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          className="h-7 gap-1 px-2 text-[10px]"
                          onClick={copyWikiIndex}
                        >
                          <Copy className="h-3 w-3" />
                          인덱스 복사
                        </Button>
                      </div>
                      {wikiIndexCopyStatus !== 'idle' && (
                        <span className={`text-[10px] ${wikiIndexCopyStatus === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                          {wikiIndexCopyStatus === 'copied' ? '복사 완료' : '복사 실패'}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2">
                    {conceptClusters.map((cluster) => (
                      <div key={cluster.concept} className="rounded-lg border border-border bg-card/60 p-3">
                        <button
                          type="button"
                          onClick={() => onFacetSelect({ type: 'concept', value: cluster.concept })}
                          className="flex w-full items-center justify-between gap-2 text-left"
                        >
                          <span className="truncate text-xs font-semibold text-foreground">
                            {cluster.concept}
                          </span>
                          <span className="shrink-0 text-[10px] text-primary">
                            {cluster.count}개 문서
                          </span>
                        </button>
                        <ul className="mt-2 space-y-1">
                          {cluster.notes.map((note) => (
                            <li key={`${cluster.concept}-${note.id}`}>
                              <Link
                                href={`/notes/${encodeURIComponent(note.id)}`}
                                className="block truncate rounded-md px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                              >
                                {note.title || '제목 없음'}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {knowledgeGaps.length > 0 && (
                <div className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                        <Brain className="h-3.5 w-3.5 text-amber-500/80" />
                        지식 공백
                      </div>
                      <p className="mt-1 text-[10px] text-muted-foreground">
                        한 문서에만 등장하는 개념입니다. 연결 노트를 추가해 지식을 확장해 보세요.
                      </p>
                    </div>
                    <span className="shrink-0 text-[10px] text-amber-600 dark:text-amber-400">
                      {knowledgeGaps.length}개
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {knowledgeGaps.map((gap) => (
                      <div key={`${gap.concept}-${gap.note.id}`} className="rounded-lg border border-border bg-card/70 p-2.5">
                        <button
                          type="button"
                          onClick={() => onFacetSelect({ type: 'concept', value: gap.concept })}
                          className="block w-full truncate text-left text-xs font-semibold text-foreground hover:text-primary"
                        >
                          {gap.concept}
                        </button>
                        <Link
                          href={`/notes/${encodeURIComponent(gap.note.id)}`}
                          className="mt-1 block truncate text-[10px] text-muted-foreground hover:text-foreground"
                        >
                          {gap.note.title || '제목 없음'}
                        </Link>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-3">
        {wikiExploreOpen && (
          <Card className="py-4">
            <CardContent className="px-4">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary/70" />
                <h2 className="text-sm font-semibold text-foreground">출처 구성</h2>
              </div>
              <div className="mt-3 space-y-2">
                {sourceGroups.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => onFacetSelect({ type: 'source', value: item.label })}
                    className="flex w-full items-center justify-between rounded-lg bg-muted/40 px-3 py-2 text-left text-xs transition-colors hover:bg-muted"
                  >
                    <span className="text-muted-foreground">{item.label}</span>
                    <span className="font-medium text-foreground">{item.count}개</span>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

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

        {(totalStudyQueueItems > 0 || recentReviewHistory.length > 0) && (
          <Card className="border-primary/20 bg-primary/5 py-4">
            <CardContent className="px-4">
              <button
                type="button"
                onClick={handleStudyQueueToggle}
                aria-expanded={studyQueueOpen}
                className="flex w-full items-center justify-between gap-3 text-left"
              >
                <span>
                  <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
                    <CheckCircle2 className="h-4 w-4 text-primary/70" />
                    학습 큐
                  </span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    복습할 노트를 우선순위대로 모았습니다.
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                  {dueReviewCount > 0 && <>오늘 복습 {dueReviewCount}개 · </>}
                  {totalStudyQueueItems}개 항목
                  <ChevronDown className={`h-4 w-4 transition-transform ${studyQueueOpen ? 'rotate-180' : ''}`} />
                </span>
              </button>

              {studyQueueOpen && (
                <div className="mt-3 grid gap-3">
                  {recallReinforcementPath && (
                    <Card className="border-primary/30 bg-background/90 py-4">
                      <CardContent className="px-4">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="min-w-0">
                            <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
                              <Brain className="h-4 w-4 text-primary" />
                              회상 보강 추천
                            </h2>
                            <p className="mt-1 text-xs text-muted-foreground">
                              막힌 개념을 연결 노트로 보강한 뒤 원래 질문을 다시 확인하세요.
                            </p>
                          </div>
                          <Badge variant="outline" className="shrink-0 text-[10px]">
                            {recallReinforcementPath.status.label}
                          </Badge>
                        </div>
                        <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                          <div className="rounded-lg border border-border bg-muted/20 px-3 py-2">
                            <span className="block text-[10px] text-muted-foreground">원본 노트</span>
                            <span className="mt-0.5 block truncate font-medium text-foreground">
                              {recallReinforcementPath.originalNote.title || '제목 없음'}
                            </span>
                          </div>
                          <div className="rounded-lg border border-primary/25 bg-primary/5 px-3 py-2">
                            <span className="block text-[10px] text-muted-foreground">연결 노트</span>
                            <span className="mt-0.5 block truncate font-medium text-foreground">
                              {recallReinforcementPath.supportNote.title || '제목 없음'}
                            </span>
                          </div>
                        </div>
                        <p className="mt-2 text-[11px] text-muted-foreground">
                          지난 회상: {recallReinforcementPath.review.grade === 'again' ? '다시' : '어려움'}
                          {' · '}
                          {recallReinforcementPath.previousIntervalDays === null
                            ? '이전 기록 없음'
                            : recallReinforcementPath.previousIntervalDays + '일'}
                          {' → '}{recallReinforcementPath.currentIntervalDays}일
                          {' · 복습 시점 '}{formatStudyUpdatedAt(recallReinforcementPath.review.completedAt)}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-1.5">
                          <span className="text-[10px] text-muted-foreground">공유 개념</span>
                          {recallReinforcementPath.sharedConcepts.map((concept) => (
                            <Badge key={concept} variant="secondary" className="text-[10px]">
                              {concept}
                            </Badge>
                          ))}
                        </div>
                        <ol className="mt-3 grid gap-2 text-xs sm:grid-cols-2" aria-label="회상 보강 단계 미리보기">
                          <li className="flex min-w-0 items-center gap-2 rounded-lg border border-primary/30 bg-background px-3 py-2">
                            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">1</span>
                            <span className="break-words">연결 노트 읽기</span>
                          </li>
                          <li className="flex min-w-0 items-center gap-2 rounded-lg border border-border bg-background/70 px-3 py-2 text-muted-foreground">
                            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-border text-[10px] font-semibold">2</span>
                            <span className="break-words">원래 질문 전체 재도전</span>
                          </li>
                        </ol>
                        <Button asChild size="sm" className="mt-3 h-auto min-h-9 w-full whitespace-normal text-center sm:w-auto">
                          <Link href={buildNoteRecallSupportHref(
                            recallReinforcementPath.originalNote.id,
                            recallReinforcementPath.supportNote.id
                          ) ?? '/notes'}>
                            보강 학습 시작
                          </Link>
                        </Button>
                      </CardContent>
                    </Card>
                  )}
                  {recentReviewHistory.length > 0 && (
                    <Card className="border-orange-500/20 bg-background/90 py-4">
                      <CardContent className="px-4">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Flame className="h-4 w-4 text-orange-500/80" />
                            <h2 className="text-sm font-semibold text-foreground">복습 기록</h2>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              className="h-7 gap-1 px-2 text-[10px]"
                              onClick={copyReviewHistory}
                            >
                              <Copy className="h-3 w-3" />
                              기록 복사
                            </Button>
                            {reviewHistoryCopyStatus !== 'idle' && (
                              <span className={`text-[10px] ${reviewHistoryCopyStatus === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                                {reviewHistoryCopyStatus === 'copied' ? '복사 완료' : '복사 실패'}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="mt-3 grid grid-cols-3 gap-2">
                          <div className="rounded-lg bg-orange-500/5 px-2 py-2 text-center">
                            <div className="text-lg font-semibold text-orange-600 dark:text-orange-400">
                              {reviewHistorySummary.currentStreak}일
                            </div>
                            <div className="text-[10px] text-muted-foreground">연속 학습</div>
                          </div>
                          <div className="rounded-lg bg-muted/40 px-2 py-2 text-center">
                            <div className="text-lg font-semibold text-foreground">
                              {reviewHistorySummary.totalCompletions}
                            </div>
                            <div className="text-[10px] text-muted-foreground">7일 완료</div>
                          </div>
                          <div className="rounded-lg bg-muted/40 px-2 py-2 text-center">
                            <div className="text-lg font-semibold text-foreground">
                              {reviewHistorySummary.activeDays}일
                            </div>
                            <div className="text-[10px] text-muted-foreground">7일 활동</div>
                          </div>
                        </div>
                        <div className="mt-3 rounded-lg border border-border/70 bg-muted/20 px-3 py-2.5">
                          <div className="mb-2 flex items-center justify-between text-[10px] text-muted-foreground">
                            <span>최근 7일 활동</span>
                            <span>복습 완료 횟수</span>
                          </div>
                          <div
                            role="img"
                            aria-label="최근 7일 복습 활동"
                            className="flex h-16 items-end justify-between gap-1.5"
                          >
                            {reviewActivityDays.map((day) => {
                              const height = day.count > 0
                                ? Math.max(8, Math.round((day.count / maxReviewActivityCount) * 42))
                                : 4;
                              return (
                                <div
                                  key={day.dateKey}
                                  title={`${day.dateKey}: ${day.count}회`}
                                  className="flex min-w-0 flex-1 flex-col items-center justify-end gap-1"
                                >
                                  <span className="text-[9px] font-medium text-muted-foreground">
                                    {day.count > 0 ? day.count : ''}
                                  </span>
                                  <span
                                    className={`w-full max-w-6 rounded-t-sm ${day.count > 0 ? 'bg-orange-500/80' : 'bg-muted'}`}
                                    style={{ height }}
                                  />
                                  <span className={`text-[9px] ${day.isToday ? 'font-semibold text-orange-600 dark:text-orange-400' : 'text-muted-foreground'}`}>
                                    {day.label}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                        <ul className="mt-3 space-y-1.5">
                          {recentReviewHistory.map((entry) => (
                            <li key={entry.id}>
                              <Link
                                href={`/notes/${encodeURIComponent(entry.noteId)}#study-progress`}
                                className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-xs transition-colors hover:bg-muted"
                              >
                                <span className="truncate text-foreground">{entry.noteTitle}</span>
                                <span className="shrink-0 text-[10px] text-muted-foreground">
                                  {formatStudyUpdatedAt(entry.completedAt)} · {entry.intervalDays}일 간격
                                </span>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}
                  {scheduledReviewItems.length > 0 && (
                    <Card className="border-amber-500/20 bg-background/90 py-4">
                      <CardContent className="px-4">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <CalendarClock className="h-4 w-4 text-amber-500/80" />
                              <h2 className="text-sm font-semibold text-foreground">예정 복습</h2>
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">
                              예약한 복습일이 가까운 순서대로 표시됩니다.
                            </p>
                          </div>
                          <span className="rounded-full bg-primary/10 px-2 py-1 text-[10px] font-semibold text-primary">
                            {scheduledReviewItems.length}개 예약
                          </span>
                        </div>
                        <ul className="mt-3 space-y-2">
                          {scheduledReviewItems.map((item) => (
                            <li key={item.note.id}>
                              <Link
                                href={`/notes/${encodeURIComponent(item.note.id)}#study-progress`}
                                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-background px-3 py-2 transition-colors hover:border-amber-500/40"
                              >
                                <span className="min-w-0">
                                  <span className="block truncate text-xs font-medium text-foreground">
                                    {item.note.title || '제목 없음'}
                                  </span>
                                  <span className="mt-0.5 block text-[10px] text-muted-foreground">
                                    {formatDate(item.schedule.dueAt)} · {item.schedule.intervalDays}일 간격
                                  </span>
                                </span>
                                <span className={`shrink-0 text-[10px] font-semibold ${item.status.state === 'due' ? 'text-amber-600 dark:text-amber-400' : 'text-primary'}`}>
                                  {item.status.label}
                                </span>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}
                  {qnaStudyCards.length > 0 && (
                    <Card className="border-primary/30 bg-background/90 py-4">
                      <CardContent className="px-4">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <MessageSquare className="h-4 w-4 text-primary/70" />
                              <h2 className="text-sm font-semibold text-foreground">Q&A 복습 카드함</h2>
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">
                              근거 Q&A에서 저장한 최근 복습 카드입니다.
                            </p>
                          </div>
                          <div className="flex shrink-0 items-center gap-2">
                            <span className="text-[10px] text-muted-foreground">
                              최근 {qnaStudyCards.length}개
                            </span>
                            <Button
                              type="button"
                              size="sm"
                              variant="outline"
                              className="h-7 gap-1 px-2 text-[10px]"
                              onClick={copyQnaStudyCards}
                            >
                              <Copy className="h-3 w-3" />
                              전체 복사
                            </Button>
                          </div>
                        </div>
                        {qnaCardsCopyStatus !== 'idle' && (
                          <p className={`mt-2 text-[10px] ${qnaCardsCopyStatus === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                            {qnaCardsCopyStatus === 'copied' ? '카드함 복사 완료' : '카드함 복사 실패'}
                          </p>
                        )}
                        <ul className="mt-3 space-y-2">
                          {qnaStudyCards.map((card) => (
                            <li key={card.id} className="rounded-lg border border-border bg-background px-3 py-2">
                              <div className="flex items-start justify-between gap-2">
                                <div className="min-w-0">
                                  <p className="truncate text-xs font-semibold text-foreground">
                                    {card.title}
                                  </p>
                                  <p className="mt-1 line-clamp-2 text-[10px] leading-relaxed text-muted-foreground">
                                    Q. {card.question}
                                  </p>
                                  <p className="mt-1 text-[10px] text-muted-foreground/70">
                                    {formatStudyUpdatedAt(card.createdAt)} · 근거 {card.sources.length}개
                                  </p>
                                </div>
                                <div className="flex shrink-0 flex-col items-end gap-1">
                                  <div className="flex flex-wrap justify-end gap-1.5">
                                    {card.sourceHref && (
                                      <Button asChild size="sm" variant="ghost" className="h-7 px-2 text-[10px]">
                                        <Link href={card.sourceHref}>원본 노트</Link>
                                      </Button>
                                    )}
                                    <Button
                                      type="button"
                                      size="sm"
                                      variant="outline"
                                      className="h-7 gap-1 px-2 text-[10px]"
                                      onClick={() => copyQnaStudyCard(card)}
                                    >
                                      <Copy className="h-3 w-3" />
                                      카드 복사
                                    </Button>
                                  </div>
                                  {qnaCardCopyStatus?.id === card.id && (
                                    <span className={`text-[10px] ${qnaCardCopyStatus.status === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                                      {qnaCardCopyStatus.status === 'copied' ? '복사 완료' : '복사 실패'}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}

                  {dailyStudyPlanItems.length > 0 && (
                    <Card className="border-primary/30 bg-background/90 py-4">
                      <CardContent className="px-4">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Brain className="h-4 w-4 text-primary/70" />
                            <h2 className="text-sm font-semibold text-foreground">오늘의 복습 플랜</h2>
                          </div>
                          <div className="flex shrink-0 flex-col items-end gap-1">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[10px] text-primary">
                                {dailyStudyPlanItems.length}단계
                              </span>
                              <Button
                                type="button"
                                size="sm"
                                variant="outline"
                                className="h-7 gap-1 px-2 text-[10px]"
                                onClick={copyDailyStudyPlan}
                              >
                                <Copy className="h-3 w-3" />
                                플랜 복사
                              </Button>
                            </div>
                            {studyPlanCopyStatus !== 'idle' && (
                              <span className={`text-[10px] ${studyPlanCopyStatus === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                                {studyPlanCopyStatus === 'copied' ? '복사 완료' : '복사 실패'}
                              </span>
                            )}
                          </div>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          진행 중인 노트를 먼저 끝내고, 남는 시간에 새 노트를 시작합니다.
                        </p>
                        <ol className="mt-3 space-y-2">
                          {dailyStudyPlanItems.map((item, index) => (
                            <li key={`${item.kind}-${item.note.id}`}>
                              <Link
                                href={`/notes/${encodeURIComponent(item.note.id)}#study-progress`}
                                className="flex items-center gap-2 rounded-lg border border-border bg-background px-3 py-2 transition-colors hover:border-primary/40"
                              >
                                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">
                                  {index + 1}
                                </span>
                                <span className="min-w-0 flex-1">
                                  <span className="block truncate text-xs font-medium text-foreground">
                                    {item.note.title || '제목 없음'}
                                  </span>
                                  <span className="mt-0.5 block text-[10px] text-muted-foreground">
                                    {item.label} · {item.remaining}개 항목
                                  </span>
                                </span>
                                <span className="shrink-0 text-[10px] font-semibold text-primary">
                                  {item.actionLabel}
                                </span>
                              </Link>
                            </li>
                          ))}
                        </ol>
                      </CardContent>
                    </Card>
                  )}

                  {studyStartNotes.length > 0 && (
                    <Card className="bg-background/80 py-4" style={studyCardOrderStyle('study-start')}>
                      <CardContent className="px-4">
                        <div className="flex items-center gap-2">
                          <BookOpen className="h-4 w-4 text-primary/70" />
                          <h2 className="text-sm font-semibold text-foreground">복습 시작</h2>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          아직 체크하지 않은 최근 학습 노트부터 시작하세요.
                        </p>
                        <ul className="mt-3 space-y-2">
                          {studyStartNotes.map((item) => (
                            <li key={item.note.id}>
                              <Link
                                href={`/notes/${encodeURIComponent(item.note.id)}#study-progress`}
                                className="block rounded-lg border border-border bg-background px-3 py-2 transition-colors hover:border-primary/40"
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <p className="truncate text-xs font-medium text-foreground">
                                    {item.note.title || '제목 없음'}
                                  </p>
                                  <span className="shrink-0 text-[10px] font-semibold text-primary">
                                    학습 {item.summary.total}개
                                  </span>
                                </div>
                                <p className="mt-1 text-[10px] text-muted-foreground">
                                  {formatDate(item.note.created_at)}
                                </p>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}

                  {reviewNeededNotes.length > 0 && (
                    <Card className="border-primary/20 bg-background/80 py-4" style={studyCardOrderStyle('review-needed')}>
                      <CardContent className="px-4">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-primary/70" />
                          <h2 className="text-sm font-semibold text-foreground">복습 필요</h2>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          진행률이 낮은 미완료 노트부터 우선 이어가세요.
                        </p>
                        <ul className="mt-3 space-y-2">
                          {reviewNeededNotes.map((item) => {
                            const remaining = item.summary.total - item.summary.completed;
                            return (
                              <li key={item.note.id}>
                                <Link
                                  href={`/notes/${encodeURIComponent(item.note.id)}#study-progress`}
                                  className="block rounded-lg border border-primary/20 bg-background px-3 py-2 transition-colors hover:border-primary/50"
                                >
                                  <div className="flex items-center justify-between gap-2">
                                    <p className="truncate text-xs font-medium text-foreground">
                                      {item.note.title || '제목 없음'}
                                    </p>
                                    <span className="shrink-0 text-[10px] font-semibold text-primary">
                                      남은 {remaining}개
                                    </span>
                                  </div>
                                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                                    <div
                                      className="h-full rounded-full bg-primary"
                                      style={{ width: `${item.summary.percent}%` }}
                                    />
                                  </div>
                                  <p className="mt-1 text-[10px] text-muted-foreground">
                                    {item.summary.completed}/{item.summary.total} 완료 · {item.summary.percent}%
                                  </p>
                                </Link>
                              </li>
                            );
                          })}
                        </ul>
                      </CardContent>
                    </Card>
                  )}

                  {completedStudyNotes.length > 0 && (
                    <Card className="bg-background/80 py-4" style={studyCardOrderStyle('completed')}>
                      <CardContent className="px-4">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-primary/70" />
                          <h2 className="text-sm font-semibold text-foreground">완료 학습</h2>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          최근 완료한 복습 노트를 따로 모아 성취를 확인하세요.
                        </p>
                        <ul className="mt-3 space-y-2">
                          {completedStudyNotes.map((item) => (
                            <li key={item.note.id}>
                              <Link
                                href={`/notes/${encodeURIComponent(item.note.id)}#study-progress`}
                                className="block rounded-lg border border-border bg-background px-3 py-2 transition-colors hover:border-primary/40"
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <p className="truncate text-xs font-medium text-foreground">
                                    {item.note.title || '제목 없음'}
                                  </p>
                                  <span className="shrink-0 text-[10px] font-semibold text-primary">
                                    완료
                                  </span>
                                </div>
                                <p className="mt-1 text-[10px] text-muted-foreground">
                                  {item.summary.completed}/{item.summary.total} 완료 · {formatStudyUpdatedAt(item.updatedAt)}
                                </p>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  )}

                  {studyResumeNotes.length > 0 && (
                    <Card className="border-primary/20 bg-background/80 py-4" style={studyCardOrderStyle('recent')}>
                      <CardContent className="px-4">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4 text-primary/70" />
                          <h2 className="text-sm font-semibold text-foreground">최근 복습</h2>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          우선·완료 목록과 겹치지 않는 최근 체크 노트입니다.
                        </p>
                        <ul className="mt-3 space-y-2">
                          {studyResumeNotes.map((item) => {
                            const completed = item.summary.completed >= item.summary.total;
                            return (
                              <li key={item.note.id}>
                                <Link
                                  href={`/notes/${encodeURIComponent(item.note.id)}#study-progress`}
                                  className="block rounded-lg border border-primary/20 bg-background px-3 py-2 transition-colors hover:border-primary/50"
                                >
                                  <div className="flex items-center justify-between gap-2">
                                    <p className="truncate text-xs font-medium text-foreground">
                                      {item.note.title || '제목 없음'}
                                    </p>
                                    <span className="shrink-0 text-[10px] font-semibold text-primary">
                                      {completed ? '완료' : `${item.summary.percent}%`}
                                    </span>
                                  </div>
                                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                                    <div
                                      className="h-full rounded-full bg-primary"
                                      style={{ width: `${item.summary.percent}%` }}
                                    />
                                  </div>
                                  <p className="mt-1 text-[10px] text-muted-foreground">
                                    {item.summary.completed}/{item.summary.total} 완료
                                  </p>
                                </Link>
                              </li>
                            );
                          })}
                        </ul>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </section>
  );
}

function NotesList({
  notes,
  studyProgressByNote,
  emptyText,
}: {
  notes: NoteListItem[];
  studyProgressByNote: Record<string, NoteStudyProgress>;
  emptyText?: string;
}) {
  if (notes.length === 0) {
    return (
      <div className="text-center py-16">
        <BookOpen className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">
          {emptyText ?? '아직 노트가 없습니다. 영상이나 아티클을 분석하면 핵심 지식이 노트로 자동 정리됩니다.'}
        </p>
      </div>
    );
  }

  return (
    <ul className="grid gap-3 md:grid-cols-2">
      {notes.map((note) => {
        const studyStatus = getNoteStudyStatus(note, studyProgressByNote[note.id]);
        const studyStatusLabel = getNoteStudyStatusLabel(studyStatus);
        return (
          <li key={note.id}>
            <Link href={`/notes/${encodeURIComponent(note.id)}`}>
              <Card className="h-full hover:border-primary/40 hover:shadow-sm transition-all cursor-pointer py-4">
                <CardContent className="px-4">
                  <div className="flex items-start gap-2.5">
                    <SourceIcon type={note.source?.type ?? ''} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <h2 className="truncate text-sm font-medium text-foreground">
                          {note.title || '제목 없음'}
                        </h2>
                        <Badge variant={studyStatus === 'completed' ? 'default' : 'outline'} className="shrink-0 text-[10px]">
                          {studyStatusLabel}
                        </Badge>
                      </div>
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
                      <span className="inline-flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        질문 {note.review_question_count ?? 0}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        </li>
        );
      })}
    </ul>
  );
}

export function SearchResultsList({
  results,
  notes,
}: {
  results: NoteSearchResult[];
  notes: NoteListItem[];
}) {
  const presentations = getNoteSearchResultPresentations(results, notes);
  const actionLinkClass = 'inline-flex items-center gap-1 rounded-sm text-xs font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2';

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
      {presentations.map(({
        result,
        hasNoteMetadata,
        keyConcepts,
        quoteCount,
        learningPointCount,
        reviewQuestionCount,
        studyCount,
        links,
      }) => {
        const title = result.title || '제목 없음';

        return (
          <li key={result.id}>
            <Card className="hover:border-primary/40 hover:shadow-sm transition-all py-4">
              <CardContent className="px-4">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="min-w-0 truncate text-sm font-medium text-foreground">
                    <Link
                      href={links.document}
                      aria-label={title + ' 문서 열기'}
                      className="rounded-sm hover:text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    >
                      {title}
                    </Link>
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
                {keyConcepts.length > 0 && (
                  <div className="mt-3 flex flex-wrap items-center gap-1.5" aria-label="핵심 개념">
                    <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                      <Tags className="h-3 w-3" />
                      핵심 개념
                    </span>
                    {keyConcepts.map((concept) => (
                      <Badge key={concept} variant="secondary" className="text-[10px] font-normal">
                        {concept}
                      </Badge>
                    ))}
                  </div>
                )}
                {hasNoteMetadata && (
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
                    <span className="inline-flex items-center gap-1">
                      <Quote className="h-3 w-3" />
                      인용 {quoteCount}
                    </span>
                    <span
                      className="inline-flex items-center gap-1"
                      aria-label={'학습과 복습 ' + studyCount + '개: 학습 포인트 ' + learningPointCount + '개, 복습 질문 ' + reviewQuestionCount + '개'}
                    >
                      <Brain className="h-3 w-3" />
                      학습·복습 {studyCount}
                      <span className="text-muted-foreground/70">
                        (포인트 {learningPointCount} · 질문 {reviewQuestionCount})
                      </span>
                    </span>
                  </div>
                )}
                <nav className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-3" aria-label={title + ' 바로가기'}>
                  <Link href={links.document} aria-label={title + ' 문서 열기'} className={actionLinkClass}>
                    <FileText className="h-3.5 w-3.5" />
                    문서 열기
                  </Link>
                  {links.quotes && (
                    <Link href={links.quotes} aria-label={title + ' 근거 보기'} className={actionLinkClass}>
                      <Quote className="h-3.5 w-3.5" />
                      근거 보기
                    </Link>
                  )}
                  {links.studyProgress && (
                    <Link href={links.studyProgress} aria-label={title + ' 복습 시작'} className={actionLinkClass}>
                      <Brain className="h-3.5 w-3.5" />
                      복습 시작
                    </Link>
                  )}
                  <Link href={links.chat} aria-label={title + ' 근거 Q&A'} className={actionLinkClass}>
                    <MessageSquare className="h-3.5 w-3.5" />
                    근거 Q&amp;A
                  </Link>
                </nav>
              </CardContent>
            </Card>
          </li>
        );
      })}
    </ul>
  );
}
