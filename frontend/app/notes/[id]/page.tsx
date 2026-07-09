'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, Brain, CheckCircle2, ExternalLink, FileText, HelpCircle, Link2, MessageSquare, Quote } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { getNote, type NoteDetail } from '@/lib/api';
import ResultChatPanel from '@/components/result/ResultChatPanel';
import { findReportLinkedToNote } from '@/lib/knowledge-note-source';
import { buildNoteOutline, type NoteOutlineItem } from '@/lib/note-outline';
import {
  getNoteStudySummary,
  normalizeNoteStudyProgress,
  readNoteStudyProgress,
  toggleNoteStudyItem,
  writeNoteStudyProgress,
  type NoteStudyCounts,
  type NoteStudyKind,
  type NoteStudyProgress,
} from '@/lib/note-study-progress';
import { getStyleLabel } from '@/lib/helpers';
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
  const noteId = params.id;
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
          <NoteBody note={note} linkedReport={linkedReport} />
        ) : null}
      </div>
    </div>
  );
}

function NoteBody({ note, linkedReport }: { note: NoteDetail; linkedReport: Report | null }) {
  const sourceUrl = note.source?.url ? safeHttpUrl(note.source.url) : null;
  const learningPoints = note.learning_points ?? [];
  const reviewQuestions = note.review_questions ?? [];
  const noteChatContext = buildNoteChatContext(note);
  const outlineItems = buildNoteOutline(note, { hasLinkedReport: Boolean(linkedReport) });
  const studyCounts: NoteStudyCounts = useMemo(
    () => ({ learning: learningPoints.length, review: reviewQuestions.length }),
    [learningPoints.length, reviewQuestions.length]
  );
  const [studyProgress, setStudyProgress] = useState<NoteStudyProgress>(() =>
    normalizeNoteStudyProgress(null, studyCounts)
  );
  const studySummary = getNoteStudySummary(studyProgress, studyCounts);

  useEffect(() => {
    setStudyProgress(readNoteStudyProgress(note.id, studyCounts));
  }, [note.id, studyCounts]);

  const toggleStudyProgress = useCallback((kind: NoteStudyKind, index: number) => {
    setStudyProgress((current) => {
      const next = toggleNoteStudyItem(current, kind, index, studyCounts);
      writeNoteStudyProgress(note.id, next, studyCounts);
      return next;
    });
  }, [note.id, studyCounts]);

  const resetStudyProgress = useCallback(() => {
    const next = normalizeNoteStudyProgress(null, studyCounts);
    writeNoteStudyProgress(note.id, next, studyCounts);
    setStudyProgress(next);
  }, [note.id, studyCounts]);

  return (
    <div className="space-y-6">
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
              <Badge key={tag} variant="secondary" className="text-[10px]">
                {tag}
              </Badge>
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

      {studySummary.total > 0 && (
        <Card id="study-progress" className="scroll-mt-24 border-primary/20 bg-primary/5 py-4">
          <CardContent className="px-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-foreground">복습 진행</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  학습 포인트와 복습 질문을 체크해 이 노트의 학습 상태를 브라우저에 저장합니다.
                </p>
              </div>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-8 shrink-0 text-xs"
                onClick={resetStudyProgress}
                disabled={studySummary.completed === 0}
              >
                초기화
              </Button>
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
          </CardContent>
        </Card>
      )}

      {/* 핵심 개념 */}
      {note.key_concepts.length > 0 && (
        <section id="concepts" className="scroll-mt-24">
          <h2 className="text-sm font-semibold text-foreground mb-2.5">핵심 개념</h2>
          <div className="flex flex-wrap gap-2">
            {note.key_concepts.map((concept, idx) => (
              <Badge key={`${concept}-${idx}`} variant="outline" className="text-xs px-2.5 py-1">
                {concept}
              </Badge>
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
              <ul className="space-y-2.5">
                {learningPoints.map((point, idx) => (
                  <li key={`${point}-${idx}`}>
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
                ))}
              </ul>
            </CardContent>
          </Card>
        </section>
      )}

      {/* 복습 질문 */}
      {reviewQuestions.length > 0 && (
        <section id="review-questions" className="scroll-mt-24">
          <h2 className="text-sm font-semibold text-foreground mb-2.5">복습 질문</h2>
          <div className="space-y-2">
            {reviewQuestions.map((item, idx) => (
              <Card key={`${item.question}-${idx}`} className="py-3">
                <CardContent className="px-4">
                  <div className="flex gap-2">
                    <HelpCircle className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                    <div>
                      <p className="text-sm font-medium text-foreground">{item.question}</p>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{item.answer}</p>
                      <button
                        type="button"
                        onClick={() => toggleStudyProgress('review', idx)}
                        aria-pressed={studyProgress.review.includes(idx)}
                        className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-border px-2 py-1 text-[10px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
                      >
                        <CheckCircle2
                          className={`h-3 w-3 ${
                            studyProgress.review.includes(idx) ? 'text-primary' : 'text-muted-foreground/40'
                          }`}
                        />
                        {studyProgress.review.includes(idx) ? '복습 완료' : '복습 체크'}
                      </button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
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
          <h2 className="text-sm font-semibold text-foreground mb-2.5">근거 인용</h2>
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
