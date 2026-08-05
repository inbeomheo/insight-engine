'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { ArrowLeft, Brain, CalendarClock, CheckCircle2, Copy, ExternalLink, Eye, EyeOff, FileText, HelpCircle, Link2, MessageSquare, Quote } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useClipboardCopy } from '@/hooks/useClipboardCopy';
import { getNote, type NoteDetail } from '@/lib/api';
import ResultChatPanel from '@/components/result/ResultChatPanel';
import { findReportLinkedToNote } from '@/lib/knowledge-note-source';
import { buildNoteOutline, type NoteOutlineItem } from '@/lib/note-outline';
import {
  normalizeReviewAnswerVisibility,
  setAllReviewAnswersVisible,
  toggleReviewAnswerVisibility,
} from '@/lib/note-review-session';
import {
  buildNoteChatSuggestedQuestions,
  buildNoteQuoteMarkdown,
  buildNoteWikiBrief,
  buildNoteWikiQuickActions,
  buildNoteWikiReadingPath,
  buildNoteWikiReadingPathMarkdown,
  type NoteWikiBriefItem,
  type NoteWikiQuickAction,
  type NoteWikiReadingPathItem,
} from '@/lib/note-wiki-brief';
import {
  buildNextNoteStudyTargetMarkdown,
  buildNoteStudyMarkdown,
  getNextNoteStudyTarget,
  getNoteStudyCompletionSummary,
  getNoteStudySummary,
  getVisibleNoteStudyIndexes,
  normalizeNoteStudyProgress,
  readNoteStudyProgress,
  toggleNoteStudyItem,
  writeNoteStudyProgress,
  type NoteStudyCounts,
  type NoteStudyKind,
  type NoteStudyProgress,
} from '@/lib/note-study-progress';
import {
  NOTE_REVIEW_GRADE_OPTIONS,
  clearNoteReviewSchedule,
  getNextReviewInterval,
  getPreviousIntervalForNewReviewSession,
  getNoteReviewScheduleStatus,
  readNoteReviewSchedule,
  writeNoteReviewSchedule,
  type NoteReviewGrade,
  type NoteReviewSchedule,
} from '@/lib/note-review-schedule';
import {
  getNoteReviewSelectionState,
  readNoteReviewHistory,
  recordNoteReviewCompletion,
} from '@/lib/note-review-history';
import { getStyleLabel } from '@/lib/helpers';
import { buildNoteFacetHref } from '@/lib/note-list';
import {
  buildNoteRecallRetryHref,
  buildNoteRecallSupportHref,
  resolveNoteRecallFlow,
  type NoteRecallFlow,
} from '@/lib/note-recall-flow';
import {
  createNoteRecallRetryState,
  getNoteRecallRetrySummary,
  toggleNoteRecallRetryItem,
  type NoteRecallRetrySummary,
} from '@/lib/note-recall-retry';
import type { Report } from '@/lib/types';
import { useResultStore } from '@/stores/resultStore';

function formatDate(iso: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
}

/** http/https 스킴만 허용 — javascript: 등 위험 스킴은 null 반환 (저장형 XSS 방지) */
function safeHttpUrl(url: string): string | null {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return null;
    return parsed.toString();
  } catch {
    return null;
  }
}

function buildNoteChatContext(note: NoteDetail): string {
  const lines = [
    `[노트 제목]\n${note.source?.title || '제목 없음'}`,
    note.summary ? `[요약]\n${note.summary}` : '',
    note.key_concepts.length > 0 ? `[핵심 개념]\n${note.key_concepts.join(', ')}` : '',
    (note.learning_points ?? []).length > 0
      ? `[학습 포인트]\n${(note.learning_points ?? []).map((point, idx) => `${idx + 1}. ${point}`).join('\n')}`
      : '',
    (note.review_questions ?? []).length > 0
      ? `[복습 질문]\n${(note.review_questions ?? []).map((item) => `Q. ${item.question}\nA. ${item.answer}`).join('\n')}`
      : '',
    note.quotes.length > 0
      ? `[근거 인용]\n${note.quotes.map((quote) => `- "${quote.text}"${quote.ref ? ` (${quote.ref})` : ''}`).join('\n')}`
      : '',
    (note.related_notes ?? []).length > 0
      ? `[관련 노트]\n${(note.related_notes ?? []).map((related) => `- ${related.title}: ${related.snippet ?? ''}`).join('\n')}`
      : '',
  ];
  return lines.filter(Boolean).join('\n\n');
}

function formatReviewDueAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '일정 확인 필요';
  return date.toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' });
}

function formatStudyUpdatedAt(iso: string | null): string {
  if (!iso) return '아직 기록 없음';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '아직 기록 없음';
  return d.toLocaleString('ko-KR', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function NoteDetailPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const noteId = params.id;
  const recallFlow = resolveNoteRecallFlow(noteId, new URLSearchParams(searchParams.toString()));
  const [note, setNote] = useState<NoteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hydrateResults = useResultStore((state) => state.hydrate);
  const reports = useResultStore((state) => state.reports);
  const linkedReport = useMemo(
    () => findReportLinkedToNote(reports, noteId),
    [reports, noteId]
  );

  useEffect(() => {
    hydrateResults();
  }, [hydrateResults]);

  useEffect(() => {
    let alive = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    getNote(noteId)
      .then((res) => {
        if (!alive) return;
        setNote(res);
        setError(null);
      })
      .catch((err) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : '노트를 불러오지 못했습니다.');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [noteId]);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 mb-6 -ml-2">
          <Link href="/notes">
            <ArrowLeft className="h-4 w-4" />
            노트 목록
          </Link>
        </Button>

        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-7 w-2/3" />
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : note ? (
          <NoteBody key={note.id} note={note} linkedReport={linkedReport} recallFlow={recallFlow} />
        ) : null}
      </div>
    </div>
  );
}

interface NoteReviewGradeWithInterval {
  value: NoteReviewGrade;
  label: string;
  intervalDays: number;
}

interface NoteRecallRetryOutcome {
  grade: NoteReviewGrade;
  label: string;
  intervalDays: number;
}

interface RecallFlowGuideProps {
  flow: NoteRecallFlow;
  retrySummary?: NoteRecallRetrySummary;
  retryOutcome?: NoteRecallRetryOutcome | null;
  reviewGradeOptions?: readonly NoteReviewGradeWithInterval[];
  onReviewGrade?: (grade: NoteReviewGrade) => void;
}

export function RecallFlowGuide({
  flow,
  retrySummary,
  retryOutcome,
  reviewGradeOptions = [],
  onReviewGrade,
}: RecallFlowGuideProps) {
  const supportHref = buildNoteRecallSupportHref(flow.originId, flow.supportId);
  const retryHref = buildNoteRecallRetryHref(flow.originId, flow.supportId);
  if (!supportHref || !retryHref) return null;

  const retryLocked = !retrySummary?.isComplete;
  const outcomeNeedsSupport = retryOutcome?.grade === 'again' || retryOutcome?.grade === 'hard';

  return (
    <Card
      id={flow.step === 'retry' ? 'study-progress' : undefined}
      className="scroll-mt-24 border-primary/30 bg-primary/5 py-4"
    >
      <CardContent className="px-4">
        <p className="text-xs font-semibold text-primary">회상 보강 2단계</p>
        <ol className="mt-3 grid gap-2 sm:grid-cols-2" aria-label="회상 보강 진행 단계">
          <li
            aria-current={flow.step === 'support' ? 'step' : undefined}
            className={'min-w-0 rounded-lg border px-3 py-2 ' + (flow.step === 'support' ? 'border-primary/40 bg-background' : 'border-border bg-background/60 text-muted-foreground')}
          >
            <span className="block break-words text-xs font-semibold">1/2 연결 노트 읽기</span>
            <span className="mt-1 block break-words text-[10px] text-muted-foreground">공유 개념을 다른 설명으로 보강합니다.</span>
          </li>
          <li
            aria-current={flow.step === 'retry' ? 'step' : undefined}
            className={'min-w-0 rounded-lg border px-3 py-2 ' + (flow.step === 'retry' ? 'border-primary/40 bg-background' : 'border-border bg-background/60 text-muted-foreground')}
          >
            <span className="block break-words text-xs font-semibold">2/2 원래 질문 재도전</span>
            <span className="mt-1 block break-words text-[10px] text-muted-foreground">
              {flow.step === 'support' ? '다음 단계에서 원래 질문 전체를 다시 풉니다.' : '답을 가린 채 질문 전체를 다시 풉니다.'}
            </span>
          </li>
        </ol>

        {flow.step === 'retry' && (
          <div className="mt-3 rounded-xl border border-primary/20 bg-background/80 p-3">
            <div className="flex items-center justify-between gap-3 text-xs font-semibold text-foreground">
              <span>재도전 진행</span>
              <span aria-live="polite">
                {retrySummary?.completed ?? 0}/{retrySummary?.total ?? 0}
              </span>
            </div>
            {retrySummary && retrySummary.total > 0 ? (
              <>
                <div
                  className="mt-2 h-2 overflow-hidden rounded-full bg-muted"
                  role="progressbar"
                  aria-label="재도전 진행률"
                  aria-valuemin={0}
                  aria-valuemax={retrySummary.total}
                  aria-valuenow={retrySummary.completed}
                >
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: String(Math.round((retrySummary.completed / retrySummary.total) * 100)) + '%' }}
                  />
                </div>
                <p id="recall-retry-rating-help" className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
                  {retrySummary.isComplete
                    ? '모든 질문을 다시 풀었습니다. 이제 회상도를 평가하세요.'
                    : '모든 질문을 다시 풀면 회상도 평가가 열립니다. ' + (retrySummary.total - retrySummary.completed) + '개 남았습니다.'}
                </p>
              </>
            ) : (
              <p id="recall-retry-rating-help" className="mt-2 text-xs text-muted-foreground">
                재도전할 복습 질문이 없습니다.
              </p>
            )}

            <div id="recall-retry-rating" className="mt-3 scroll-mt-24 border-t border-border pt-3">
              <p className="text-xs font-semibold text-foreground">회상도 평가</p>
              <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label="재도전 회상도 선택">
                {reviewGradeOptions.map(({ value, label, intervalDays }) => (
                  <Button
                    key={value}
                    type="button"
                    size="sm"
                    variant={retryOutcome?.grade === value ? 'default' : 'outline'}
                    className="h-7 px-2.5 text-[10px]"
                    onClick={() => onReviewGrade?.(value)}
                    disabled={retryLocked || !onReviewGrade}
                    aria-pressed={retryOutcome?.grade === value}
                    aria-describedby="recall-retry-rating-help"
                  >
                    {label} · {intervalDays}일
                  </Button>
                ))}
              </div>
              <p className="mt-2 min-h-4 text-[10px] text-muted-foreground" role="status" aria-live="polite">
                {retryOutcome
                  ? '평가 결과: ' + retryOutcome.label + ' · 다음 복습 ' + retryOutcome.intervalDays + '일 후'
                  : !retrySummary || retrySummary.total === 0
                    ? '평가할 질문이 없어 회상도를 선택할 수 없습니다.'
                    : retryLocked
                      ? '질문을 모두 완료하기 전에는 회상도를 선택할 수 없습니다.'
                      : '회상도를 선택하면 다음 복습 간격을 예약합니다.'}
              </p>
            </div>
          </div>
        )}

        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
          {flow.step === 'support' ? (
            <Button asChild size="sm" className="h-auto min-h-9 w-full whitespace-normal text-center sm:w-auto">
              <Link href={retryHref}>읽기 마치고 원래 질문 재도전</Link>
            </Button>
          ) : retryOutcome ? (
            outcomeNeedsSupport ? (
              <Button asChild size="sm" variant="outline" className="h-auto min-h-9 w-full whitespace-normal text-center sm:w-auto">
                <Link href={supportHref}>연결 노트 다시 보기</Link>
              </Button>
            ) : (
              <Button asChild size="sm" className="h-auto min-h-9 w-full whitespace-normal text-center sm:w-auto">
                <Link href="/notes">노트 목록으로</Link>
              </Button>
            )
          ) : (
            <Button asChild size="sm" variant="outline" className="h-auto min-h-9 w-full whitespace-normal text-center sm:w-auto">
              <Link href={supportHref}>연결 노트 다시 보기</Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function NoteBody({
  note,
  linkedReport,
  recallFlow,
}: {
  note: NoteDetail;
  linkedReport: Report | null;
  recallFlow: NoteRecallFlow | null;
}) {
  const sourceUrl = note.source?.url ? safeHttpUrl(note.source.url) : null;
  const learningPoints = useMemo(() => note.learning_points ?? [], [note.learning_points]);
  const reviewQuestions = useMemo(() => note.review_questions ?? [], [note.review_questions]);
  const noteTitle = note.source?.title || '제목 없음';
  const quoteCount = note.quotes.length;
  const relatedNoteCount = note.related_notes?.length ?? 0;
  const hasLinkedReport = Boolean(linkedReport);
  const noteChatContext = buildNoteChatContext(note);
  const outlineItems = useMemo(
    () => buildNoteOutline(note, { hasLinkedReport }),
    [hasLinkedReport, note]
  );
  const studyCounts: NoteStudyCounts = useMemo(
    () => ({ learning: learningPoints.length, review: reviewQuestions.length }),
    [learningPoints.length, reviewQuestions.length]
  );
  const [studyProgress, setStudyProgress] = useState<NoteStudyProgress>(() =>
    normalizeNoteStudyProgress(null, studyCounts)
  );
  const { status: studyCopyStatus, copyText: copyStudyText } = useClipboardCopy();
  const [reviewSchedule, setReviewSchedule] = useState<NoteReviewSchedule | null>(null);
  const [previousReviewIntervalDays, setPreviousReviewIntervalDays] = useState<number | null>(null);
  const [selectedReviewGrade, setSelectedReviewGrade] = useState<NoteReviewGrade | null>(null);
  const { status: nextStudyCopyStatus, copyText: copyNextStudyText } = useClipboardCopy();
  const { status: quoteCopyStatus, copyText: copyQuoteText } = useClipboardCopy();
  const [showCompletedStudyItems, setShowCompletedStudyItems] = useState(true);
  const [reviewAnswerVisible, setReviewAnswerVisible] = useState<boolean[]>(() =>
    normalizeReviewAnswerVisibility(null, reviewQuestions.length)
  );
  const isRecallRetry = recallFlow?.step === 'retry';
  const [recallRetryState, setRecallRetryState] = useState(() =>
    createNoteRecallRetryState(reviewQuestions.length)
  );
  const [recallRetryOutcome, setRecallRetryOutcome] = useState<NoteRecallRetryOutcome | null>(null);
  const [recallRetryBaseIntervalDays, setRecallRetryBaseIntervalDays] = useState<number | null>(null);
  const recallRetrySummary = useMemo(
    () => getNoteRecallRetrySummary(recallRetryState, reviewQuestions.length),
    [recallRetryState, reviewQuestions.length]
  );
  const studySummary = useMemo(
    () => getNoteStudySummary(studyProgress, studyCounts),
    [studyCounts, studyProgress]
  );
  const studyCompletion = useMemo(
    () => getNoteStudyCompletionSummary(studySummary),
    [studySummary]
  );
  const reviewScheduleStatus = useMemo(
    () => reviewSchedule ? getNoteReviewScheduleStatus(reviewSchedule) : null,
    [reviewSchedule]
  );
  const reviewIntervalBaseDays = isRecallRetry
    ? recallRetryBaseIntervalDays
    : previousReviewIntervalDays;
  const reviewGradeOptions = useMemo(
    () => NOTE_REVIEW_GRADE_OPTIONS.map((option) => ({
      ...option,
      intervalDays: getNextReviewInterval(
        option.value,
        reviewIntervalBaseDays ?? undefined
      ),
    })),
    [reviewIntervalBaseDays]
  );
  const nextStudyTarget = useMemo(
    () => getNextNoteStudyTarget({ learningPoints, reviewQuestions, progress: studyProgress }),
    [learningPoints, reviewQuestions, studyProgress]
  );
  const allReviewAnswersVisible = reviewQuestions.length > 0 && reviewAnswerVisible.every(Boolean);
  const visibleLearningIndexes = useMemo(
    () => getVisibleNoteStudyIndexes(learningPoints.length, studyProgress.learning, showCompletedStudyItems),
    [learningPoints.length, showCompletedStudyItems, studyProgress.learning]
  );
  const visibleReviewIndexes = useMemo(
    () => recallFlow?.step === 'retry'
      ? reviewQuestions.map((_, index) => index)
      : getVisibleNoteStudyIndexes(reviewQuestions.length, studyProgress.review, showCompletedStudyItems),
    [recallFlow?.step, reviewQuestions, showCompletedStudyItems, studyProgress.review]
  );
  const wikiBriefInput = useMemo(() => ({
    sourceType: note.source?.type,
    outlineItems,
    studySummary,
    quoteCount,
    relatedNoteCount,
    hasLinkedReport,
  }), [hasLinkedReport, note.source?.type, outlineItems, quoteCount, relatedNoteCount, studySummary]);
  const wikiBriefItems = useMemo(() => buildNoteWikiBrief(wikiBriefInput), [wikiBriefInput]);
  const wikiQuickActions = useMemo(() => buildNoteWikiQuickActions(wikiBriefInput), [wikiBriefInput]);
  const chatSuggestedQuestions = useMemo(
    () => buildNoteChatSuggestedQuestions(wikiBriefInput),
    [wikiBriefInput]
  );
  const wikiReadingPathItems = useMemo(
    () => buildNoteWikiReadingPath(note.related_notes ?? [], 3),
    [note.related_notes]
  );

  useEffect(() => {
    // 브라우저 저장값은 hydration 이후에만 반영합니다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStudyProgress(readNoteStudyProgress(note.id, studyCounts));
  }, [note.id, studyCounts]);

  useEffect(() => {
    // 브라우저 저장값은 hydration 이후에만 반영합니다.
    const schedule = readNoteReviewSchedule(note.id);
    const selection = getNoteReviewSelectionState(
      readNoteReviewHistory(),
      note.id,
      schedule
    );
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setReviewSchedule(schedule);
    setPreviousReviewIntervalDays(selection.previousIntervalDays);
    setSelectedReviewGrade(selection.selectedGrade);
  }, [note.id]);

  const clearScheduledReview = useCallback(() => {
    clearNoteReviewSchedule(note.id);
    setReviewSchedule(null);
    setSelectedReviewGrade(null);
  }, [note.id]);

  const toggleStudyProgress = useCallback((kind: NoteStudyKind, index: number) => {
    setStudyProgress((current) => {
      const next = toggleNoteStudyItem(current, kind, index, studyCounts);
      writeNoteStudyProgress(note.id, next, studyCounts);
      const nextSummary = getNoteStudySummary(next, studyCounts);
      if (reviewSchedule && nextSummary.completed < nextSummary.total) {
        clearNoteReviewSchedule(note.id);
        setReviewSchedule(null);
        setSelectedReviewGrade(null);
      }
      return next;
    });
  }, [note.id, reviewSchedule, studyCounts]);

  const toggleReviewProgress = useCallback((index: number) => {
    if (isRecallRetry) {
      if (recallRetryOutcome) return;
      setRecallRetryState((current) =>
        toggleNoteRecallRetryItem(current, index, reviewQuestions.length)
      );
      return;
    }
    toggleStudyProgress('review', index);
  }, [
    isRecallRetry,
    recallRetryOutcome,
    reviewQuestions.length,
    toggleStudyProgress,
  ]);

  const resetStudyProgress = useCallback(() => {
    const next = normalizeNoteStudyProgress(null, studyCounts);
    writeNoteStudyProgress(note.id, next, studyCounts);
    setPreviousReviewIntervalDays(
      getPreviousIntervalForNewReviewSession(reviewSchedule, previousReviewIntervalDays)
    );
    clearScheduledReview();
    setStudyProgress(next);
  }, [
    clearScheduledReview,
    note.id,
    previousReviewIntervalDays,
    reviewSchedule,
    studyCounts,
  ]);

  const scheduleReview = useCallback((grade: NoteReviewGrade) => {
    if (isRecallRetry && !recallRetrySummary.isComplete) return;

    const intervalDays = getNextReviewInterval(
      grade,
      reviewIntervalBaseDays ?? undefined
    );
    const next = writeNoteReviewSchedule(note.id, intervalDays);
    if (next) {
      recordNoteReviewCompletion({
        noteId: note.id,
        noteTitle,
        intervalDays,
        grade,
        baseIntervalDays: reviewIntervalBaseDays,
        scheduleScheduledAt: next.scheduledAt,
      });
      setSelectedReviewGrade(grade);
      if (isRecallRetry) {
        const label = NOTE_REVIEW_GRADE_OPTIONS.find((option) => option.value === grade)?.label ?? grade;
        setRecallRetryOutcome({ grade, label, intervalDays });
      }
    }
    setReviewSchedule(next);
  }, [
    isRecallRetry,
    note.id,
    noteTitle,
    recallRetrySummary.isComplete,
    reviewIntervalBaseDays,
  ]);

  const scrollToNextStudyTarget = useCallback(() => {
    if (!nextStudyTarget) return;
    document.getElementById(nextStudyTarget.targetId)?.scrollIntoView({
      behavior: 'smooth',
      block: 'center',
    });
  }, [nextStudyTarget]);

  const copyNextStudyTarget = useCallback(
    () => copyNextStudyText(() => buildNextNoteStudyTargetMarkdown({
      noteTitle,
      target: nextStudyTarget,
    })),
    [copyNextStudyText, nextStudyTarget, noteTitle],
  );

  const copyQuoteMarkdown = useCallback(
    () => copyQuoteText(() => buildNoteQuoteMarkdown(note.quotes, `${noteTitle} 근거 인용`)),
    [copyQuoteText, note.quotes, noteTitle],
  );

  const toggleReviewAnswer = useCallback((index: number) => {
    setReviewAnswerVisible((current) =>
      toggleReviewAnswerVisibility(current, index, reviewQuestions.length)
    );
  }, [reviewQuestions.length]);

  const setAllReviewAnswers = useCallback((visible: boolean) => {
    setReviewAnswerVisible(setAllReviewAnswersVisible(reviewQuestions.length, visible));
  }, [reviewQuestions.length]);

  const copyStudyMarkdown = useCallback(
    () => copyStudyText(() => buildNoteStudyMarkdown({
      title: noteTitle,
      sourceUrl: sourceUrl ?? undefined,
      learningPoints,
      reviewQuestions,
      progress: studyProgress,
    })),
    [copyStudyText, learningPoints, noteTitle, reviewQuestions, sourceUrl, studyProgress],
  );

  useEffect(() => {
    if (recallFlow?.step !== 'retry') return;
    // 재도전 임시 진행과 답 표시만 초기화하며 저장 진행률·일정·이력은 건드리지 않습니다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRecallRetryState(createNoteRecallRetryState(reviewQuestions.length));
    setRecallRetryOutcome(null);
    const activeSchedule = readNoteReviewSchedule(note.id);
    const selection = getNoteReviewSelectionState(
      readNoteReviewHistory(),
      note.id,
      activeSchedule
    );
    setRecallRetryBaseIntervalDays(
      activeSchedule?.intervalDays ?? selection.previousIntervalDays
    );
    setReviewAnswerVisible(setAllReviewAnswersVisible(reviewQuestions.length, false));
    const frame = window.requestAnimationFrame(() => {
      document.getElementById('review-questions')?.scrollIntoView({ block: 'start' });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [
    note.id,
    recallFlow?.originId,
    recallFlow?.step,
    recallFlow?.supportId,
    reviewQuestions.length,
  ]);

  return (
    <div className="space-y-6">
      {recallFlow && (
        <RecallFlowGuide
          flow={recallFlow}
          retrySummary={isRecallRetry ? recallRetrySummary : undefined}
          retryOutcome={isRecallRetry ? recallRetryOutcome : null}
          reviewGradeOptions={reviewGradeOptions}
          onReviewGrade={scheduleReview}
        />
      )}
      {/* 헤더: 제목 + 출처 */}
      <div id="source" className="scroll-mt-24 rounded-2xl border border-border bg-card/60 p-5">
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-[10px] font-medium text-primary">
          <Brain className="h-3 w-3" />
          지식 노트
        </div>
        <h1 className="text-xl font-semibold text-foreground leading-snug">
          {note.source?.title || '제목 없음'}
        </h1>
        <div className="flex items-center gap-2 mt-2 flex-wrap">
          <span className="text-xs text-muted-foreground/70">{formatDate(note.created_at)}</span>
          {sourceUrl ? (
            <a
              href={sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
            >
              원본 보기
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : note.source?.url ? (
            <span className="text-xs text-muted-foreground/60">{note.source.url}</span>
          ) : null}
        </div>
        <div className="mt-4 grid gap-2 sm:grid-cols-4">
          <MiniStat label="개념" value={note.key_concepts.length} />
          <MiniStat label="포인트" value={learningPoints.length} />
          <MiniStat label="인용" value={note.quotes.length} />
          <MiniStat label="관련" value={note.related_notes?.length ?? 0} />
        </div>
        {note.tags.length > 0 && (
          <div className="flex items-center gap-1.5 mt-3 flex-wrap">
            {note.tags.map((tag) => (
              <Link
                key={tag}
                href={buildNoteFacetHref({ type: 'tag', value: tag })}
                className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Badge variant="secondary" className="cursor-pointer text-[10px] hover:bg-primary/10">
                  {tag}
                </Badge>
              </Link>
            ))}
          </div>
        )}
      </div>

      {linkedReport && (
        <Card id="source-result" className="scroll-mt-24 border-primary/20 bg-primary/5 py-3">
          <CardContent className="px-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-start gap-2.5">
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary/75" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-foreground">원본 결과 카드</p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {linkedReport.title || '제목 없음'}
                  </p>
                  <p className="mt-1 text-[10px] text-muted-foreground/70">
                    {getStyleLabel(linkedReport.style)} · {linkedReport.time}
                  </p>
                </div>
              </div>
              <Button asChild size="sm" variant="outline" className="shrink-0">
                <Link href={`/?report=${encodeURIComponent(linkedReport.id)}`}>결과 열기</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <NoteOutline items={outlineItems} />
      <NoteWikiBrief items={wikiBriefItems} actions={wikiQuickActions} />
      {wikiReadingPathItems.length > 0 && (
        <NoteWikiReadingPath
          title={note.source?.title || '제목 없음'}
          items={wikiReadingPathItems}
        />
      )}

      {studySummary.total > 0 && !isRecallRetry && (
        <Card id="study-progress" className="scroll-mt-24 border-primary/20 bg-primary/5 py-4">
          <CardContent className="px-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-foreground">복습 진행</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  학습 포인트와 복습 질문을 체크해 이 노트의 학습 상태를 브라우저에 저장합니다.
                </p>
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1">
                <div className="flex gap-1.5">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs"
                    onClick={copyStudyMarkdown}
                    disabled={studySummary.total === 0}
                  >
                    <Copy className="mr-1 h-3 w-3" />
                    Markdown 복사
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs"
                    onClick={() => setShowCompletedStudyItems((value) => !value)}
                    disabled={studySummary.completed === 0}
                  >
                    {showCompletedStudyItems ? '완료 숨기기' : '전체 보기'}
                  </Button>
                  {!studyCompletion.complete && (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="h-8 text-xs"
                      onClick={resetStudyProgress}
                      disabled={studySummary.completed === 0}
                    >
                      초기화
                    </Button>
                  )}
                </div>
                {studyCopyStatus !== 'idle' && (
                  <span className={`text-[10px] ${studyCopyStatus === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                    {studyCopyStatus === 'copied' ? '복사 완료' : '복사 실패'}
                  </span>
                )}
              </div>
            </div>
            <div className="mt-4 flex items-end justify-between gap-3">
              <div>
                <div className="text-2xl font-semibold text-foreground">{studySummary.percent}%</div>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {studySummary.completed} / {studySummary.total} 완료 · {formatStudyUpdatedAt(studyProgress.updatedAt)}
                </div>
              </div>
              <div className="text-right text-xs text-muted-foreground">
                <div>포인트 {studySummary.completedLearning}/{studyCounts.learning}</div>
                <div>질문 {studySummary.completedReview}/{studyCounts.review}</div>
              </div>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-background">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${studySummary.percent}%` }}
              />
            </div>
            {nextStudyTarget && (
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/20 bg-background/80 px-3 py-3">
                <div className="min-w-0">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-primary">다음 복습</p>
                  <p className="mt-1 text-sm font-semibold text-foreground">{nextStudyTarget.label}</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {nextStudyTarget.title}
                  </p>
                  <p className="mt-1 text-[10px] text-muted-foreground/70">{nextStudyTarget.description}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <div className="flex gap-1.5">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs"
                      onClick={copyNextStudyTarget}
                    >
                      <Copy className="mr-1 h-3 w-3" />
                      복사
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-8 text-xs"
                      onClick={scrollToNextStudyTarget}
                    >
                      이동
                    </Button>
                  </div>
                  {nextStudyCopyStatus !== 'idle' && (
                    <span className={`text-[10px] ${nextStudyCopyStatus === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                      {nextStudyCopyStatus === 'copied' ? '복사 완료' : '복사 실패'}
                    </span>
                  )}
                </div>
              </div>
            )}
            {studyCompletion.complete && (
              <div className="mt-4 rounded-xl border border-primary/20 bg-background/80 px-3 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    <div>
                      <p className="text-sm font-semibold text-foreground">복습 세션 완료</p>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {studyCompletion.message} 다음 복습일을 예약해 기억을 다시 확인하세요.
                      </p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="h-8 shrink-0 text-xs"
                    onClick={resetStudyProgress}
                  >
                    {studyCompletion.actionLabel}
                  </Button>
                </div>
                <div className="mt-3 rounded-lg border border-border bg-card/70 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <CalendarClock className="h-3.5 w-3.5 text-primary/70" />
                      <span className="text-xs font-semibold text-foreground">다음 복습 예약</span>
                    </div>
                    {reviewSchedule && reviewScheduleStatus && (
                      <span className={`text-[10px] font-medium ${reviewScheduleStatus.state === 'due' ? 'text-amber-600 dark:text-amber-400' : 'text-primary'}`}>
                        {reviewScheduleStatus.label} · {formatReviewDueAt(reviewSchedule.dueAt)}
                      </span>
                    )}
                  </div>
                  <div
                    className="mt-2 flex flex-wrap gap-1.5"
                    role="group"
                    aria-label="회상도 선택"
                  >
                    {reviewGradeOptions.map(({ value, label, intervalDays }) => (
                      <Button
                        key={value}
                        type="button"
                        size="sm"
                        variant={selectedReviewGrade === value ? 'default' : 'outline'}
                        className="h-7 px-2.5 text-[10px]"
                        onClick={() => scheduleReview(value)}
                        aria-pressed={selectedReviewGrade === value}
                      >
                        {label} · {intervalDays}일
                      </Button>
                    ))}
                    {reviewSchedule && (
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-[10px]"
                        onClick={clearScheduledReview}
                      >
                        일정 해제
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 핵심 개념 */}
      {note.key_concepts.length > 0 && (
        <section id="concepts" className="scroll-mt-24">
          <h2 className="text-sm font-semibold text-foreground mb-2.5">핵심 개념</h2>
          <div className="flex flex-wrap gap-2">
            {note.key_concepts.map((concept, idx) => (
              <Link
                key={`${concept}-${idx}`}
                href={buildNoteFacetHref({ type: 'concept', value: concept })}
                className="rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Badge variant="outline" className="cursor-pointer px-2.5 py-1 text-xs hover:border-primary/40 hover:text-primary">
                  {concept}
                </Badge>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* 학습 포인트 */}
      {learningPoints.length > 0 && (
        <section id="learning-points" className="scroll-mt-24">
          <h2 className="text-sm font-semibold text-foreground mb-2.5">학습 포인트</h2>
          <Card className="py-4">
            <CardContent className="px-4">
              {visibleLearningIndexes.length === 0 ? (
                <p className="text-sm text-muted-foreground">모든 학습 포인트를 완료했습니다.</p>
              ) : (
                <ul className="space-y-2.5">
                  {visibleLearningIndexes.map((idx) => {
                    const point = learningPoints[idx];
                    return (
                      <li key={`${point}-${idx}`} id={`study-learning-${idx}`} className="scroll-mt-24">
                        <button
                          type="button"
                          onClick={() => toggleStudyProgress('learning', idx)}
                          aria-pressed={studyProgress.learning.includes(idx)}
                          className="flex w-full gap-2 rounded-lg px-1 py-1 text-left text-sm leading-relaxed text-foreground/90 transition-colors hover:bg-muted/50"
                        >
                          <CheckCircle2
                            className={`mt-0.5 h-4 w-4 shrink-0 ${
                              studyProgress.learning.includes(idx) ? 'text-primary' : 'text-muted-foreground/40'
                            }`}
                          />
                          <span className={studyProgress.learning.includes(idx) ? 'text-muted-foreground line-through' : ''}>
                            {point}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        </section>
      )}

      {/* 복습 질문 */}
      {reviewQuestions.length > 0 && (
        <section id="review-questions" className="scroll-mt-24">
          <div className="mb-2.5 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold text-foreground">복습 질문</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                답을 떠올린 뒤 열어보며 능동 회상으로 복습합니다.
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 shrink-0 text-xs"
              onClick={() => setAllReviewAnswers(!allReviewAnswersVisible)}
            >
              {allReviewAnswersVisible ? (
                <EyeOff className="mr-1 h-3 w-3" />
              ) : (
                <Eye className="mr-1 h-3 w-3" />
              )}
              {allReviewAnswersVisible ? '전체 가리기' : '전체 답 보기'}
            </Button>
          </div>
          <div className="space-y-2">
            {visibleReviewIndexes.length === 0 ? (
              <Card className="py-3">
                <CardContent className="px-4">
                  <p className="text-sm text-muted-foreground">모든 복습 질문을 완료했습니다.</p>
                </CardContent>
              </Card>
            ) : (
              visibleReviewIndexes.map((idx) => {
                const item = reviewQuestions[idx];
                const isReviewComplete = isRecallRetry
                  ? recallRetryState.completedIndexes.includes(idx)
                  : studyProgress.review.includes(idx);
                return (
                  <Card key={`${item.question}-${idx}`} id={`study-review-${idx}`} className="scroll-mt-24 py-3">
                    <CardContent className="px-4">
                      <div className="flex gap-2">
                        <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                        <div>
                          <p className="text-sm font-medium text-foreground">{item.question}</p>
                          {item.answer?.trim() ? (
                            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                              {reviewAnswerVisible[idx] ? item.answer : '답을 떠올린 뒤 열어보세요.'}
                            </p>
                          ) : (
                            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">등록된 답변이 없습니다.</p>
                          )}
                          {item.answer?.trim() && (
                            <button
                              type="button"
                              onClick={() => toggleReviewAnswer(idx)}
                              aria-expanded={reviewAnswerVisible[idx]}
                              className="mt-2 mr-1.5 inline-flex items-center gap-1.5 rounded-full border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
                            >
                              {reviewAnswerVisible[idx] ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                              {reviewAnswerVisible[idx] ? '답 가리기' : '답 보기'}
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => toggleReviewProgress(idx)}
                            aria-pressed={isReviewComplete}
                            disabled={isRecallRetry && Boolean(recallRetryOutcome)}
                            className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <CheckCircle2
                              className={'h-3 w-3 ' + (
                                isReviewComplete ? 'text-primary' : 'text-muted-foreground/40'
                              )}
                            />
                            {isReviewComplete
                              ? isRecallRetry ? '재도전 완료' : '복습 완료'
                              : '복습 체크'}
                          </button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>
        </section>
      )}

      {/* 요약 */}
      {note.summary && (
        <section id="summary" className="scroll-mt-24">
          <h2 className="text-sm font-semibold text-foreground mb-2.5">요약</h2>
          <Card className="py-4">
            <CardContent className="px-4">
              <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                {note.summary}
              </p>
            </CardContent>
          </Card>
        </section>
      )}

      {/* 근거 기반 채팅 진입 */}
      <section id="chat" className="scroll-mt-24">
        <Card className="border-primary/20 bg-primary/5 py-4">
          <CardContent className="px-4">
            <div className="flex items-start gap-3">
              <MessageSquare className="mt-0.5 h-5 w-5 shrink-0 text-primary/80" />
              <div className="min-w-0">
                <h2 className="text-sm font-semibold text-foreground">근거 기반 채팅</h2>
                <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                  이 노트의 요약·인용·관련 노트를 질문의 근거로 이어갈 수 있습니다.
                  아래 패널에서 바로 질문하거나, 관련 노트를 열어 맥락을 넓혀보세요.
                </p>
              </div>
            </div>
            <ResultChatPanel
              context={noteChatContext}
              title="노트 근거 Q&A"
              emptyText="이 노트의 요약, 학습 포인트, 인용, 관련 노트를 근거로 질문해보세요."
              placeholder="예: 이 노트에서 바로 실행할 수 있는 행동은?"
              suggestedQuestions={chatSuggestedQuestions}
              studyCardTitle={note.source?.title || '제목 없음'}
              studyCardSourceHref={`/notes/${encodeURIComponent(note.id)}`}
            />
          </CardContent>
        </Card>
      </section>

      {/* 관련 노트 */}
      {note.related_notes && note.related_notes.length > 0 && (
        <section id="related-notes" className="scroll-mt-24">
          <h2 className="text-sm font-semibold text-foreground mb-2.5">관련 노트</h2>
          <ul className="space-y-2">
            {note.related_notes.slice(0, 3).map((related) => (
              <li key={related.id}>
                <Link
                  href={`/notes/${encodeURIComponent(related.id)}`}
                  className="block rounded-lg border border-border bg-card px-3 py-2.5 transition-colors hover:border-primary/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <Link2 className="h-3.5 w-3.5 text-primary/70 shrink-0" />
                        <p className="truncate text-sm font-medium text-foreground">
                          {related.title || '제목 없음'}
                        </p>
                      </div>
                      {related.snippet && (
                        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                          {related.snippet}
                        </p>
                      )}
                    </div>
                    <Badge variant="outline" className="shrink-0 text-[10px]">
                      {Math.round(related.score * 100)}%
                    </Badge>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* 인용구 */}
      {note.quotes.length > 0 && (
        <section id="quotes" className="scroll-mt-24">
          <div className="mb-2.5 flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-foreground">근거 인용</h2>
            <div className="flex shrink-0 flex-col items-end gap-1">
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-8 text-xs"
                onClick={copyQuoteMarkdown}
              >
                <Copy className="mr-1 h-3 w-3" />
                인용 복사
              </Button>
              {quoteCopyStatus !== 'idle' && (
                <span className={`text-[10px] ${quoteCopyStatus === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                  {quoteCopyStatus === 'copied' ? '복사 완료' : '복사 실패'}
                </span>
              )}
            </div>
          </div>
          <ul className="space-y-2.5">
            {note.quotes.map((quote, idx) => (
              <li key={idx} className="flex gap-2.5 border-l-2 border-primary/30 pl-3">
                <Quote className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-sm text-foreground/90 italic">{quote.text}</p>
                  {quote.ref && (
                    <span className="text-xs text-muted-foreground/60 mt-1 block">{quote.ref}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function NoteWikiReadingPath({ title, items }: { title: string; items: NoteWikiReadingPathItem[] }) {
  const { status: copyStatus, copyText } = useClipboardCopy();
  const copyReadingPath = useCallback(
    () => copyText(() => buildNoteWikiReadingPathMarkdown(items, title)),
    [copyText, items, title],
  );
  return (
    <Card id="wiki-reading-path" className="scroll-mt-24 border-primary/20 bg-primary/5 py-4">
      <CardContent className="px-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground">위키 읽기 경로</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              현재 문서를 읽은 뒤 이어서 보면 좋은 관련 문서입니다.
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <div className="flex items-center gap-1.5">
              <span className="rounded-full border border-primary/20 bg-background/80 px-2 py-1 text-[10px] font-medium text-primary">
                {items.length}개 연결
              </span>
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-7 gap-1 px-2 text-[10px]"
                onClick={copyReadingPath}
              >
                <Copy className="h-3 w-3" />
                경로 복사
              </Button>
            </div>
            {copyStatus !== 'idle' && (
              <span className={`text-[10px] ${copyStatus === 'copied' ? 'text-primary' : 'text-destructive'}`}>
                {copyStatus === 'copied' ? '복사 완료' : '복사 실패'}
              </span>
            )}
          </div>
        </div>
        <ol className="space-y-2">
          {items.map((item, index) => (
            <li key={item.id}>
              <Link
                href={item.href}
                className="flex items-start gap-2 rounded-xl border border-border bg-background/80 px-3 py-2.5 transition-colors hover:border-primary/40"
              >
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-semibold text-foreground">{item.title}</span>
                    <span className="shrink-0 text-[10px] font-medium text-primary">{item.scorePercent}%</span>
                  </span>
                  <span className="mt-1 block text-[10px] font-medium text-primary/80">{item.label}</span>
                  <span className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                    {item.description}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

function NoteWikiBrief({ items, actions }: { items: NoteWikiBriefItem[]; actions: NoteWikiQuickAction[] }) {
  return (
    <Card id="wiki-brief" className="scroll-mt-24 border-primary/10 bg-card/80 py-4">
      <CardContent className="px-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground">문서 브리핑</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              이 지식 노트의 출처, 학습 상태, 근거 연결을 한눈에 확인합니다.
            </p>
          </div>
          <div className="hidden rounded-full border border-primary/20 bg-primary/5 px-2.5 py-1 text-[10px] font-medium text-primary sm:block">
            LLMWiki
          </div>
        </div>
        <div className="grid gap-2 sm:grid-cols-5">
          {items.map((item) => (
            <div key={item.label} className="rounded-xl border border-border bg-background/70 px-3 py-2.5">
              <div className="text-[10px] text-muted-foreground">{item.label}</div>
              <div className="mt-1 text-sm font-semibold text-foreground">{item.value}</div>
              <div className="mt-1 text-[10px] leading-snug text-muted-foreground/70">{item.description}</div>
            </div>
          ))}
        </div>
        {actions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {actions.map((action, index) => (
              <a
                key={`${action.href}-${action.label}`}
                href={action.href}
                className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs transition-colors ${
                  index === 0
                    ? 'border-primary/30 bg-primary/5 font-medium text-primary hover:border-primary/50'
                    : 'border-border bg-background/80 text-muted-foreground hover:border-primary/40 hover:text-primary'
                }`}
              >
                {index === 0 ? `추천: ${action.label}` : action.label}
              </a>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function NoteOutline({ items }: { items: NoteOutlineItem[] }) {
  return (
    <Card className="py-3">
      <CardContent className="px-4">
        <div className="mb-2 flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-foreground">문서 목차</h2>
          <span className="text-[10px] text-muted-foreground">문서 이동</span>
        </div>
        <nav aria-label="노트 문서 목차" className="flex flex-wrap gap-1.5">
          {items.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className="inline-flex items-center gap-1 rounded-full border border-border bg-background/80 px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
            >
              {item.label}
              {typeof item.count === 'number' && (
                <span className="rounded-full bg-muted px-1.5 text-[10px] text-muted-foreground">
                  {item.count}
                </span>
              )}
            </a>
          ))}
        </nav>
      </CardContent>
    </Card>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-background/70 px-3 py-2">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className="text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}
