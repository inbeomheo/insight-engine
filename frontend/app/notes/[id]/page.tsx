'use client';

import { useEffect, useMemo, useState } from 'react';
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
  return (
    <div className="space-y-6">
      {/* 헤더: 제목 + 출처 */}
      <div className="rounded-2xl border border-border bg-card/60 p-5">
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
        <Card className="border-primary/20 bg-primary/5 py-3">
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

      {/* 핵심 개념 */}
      {note.key_concepts.length > 0 && (
        <section>
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
        <section>
          <h2 className="text-sm font-semibold text-foreground mb-2.5">학습 포인트</h2>
          <Card className="py-4">
            <CardContent className="px-4">
              <ul className="space-y-2.5">
                {learningPoints.map((point, idx) => (
                  <li key={`${point}-${idx}`} className="flex gap-2 text-sm leading-relaxed text-foreground/90">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </section>
      )}

      {/* 복습 질문 */}
      {reviewQuestions.length > 0 && (
        <section>
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
        <section>
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
      <section>
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
        <section>
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
        <section>
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

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-background/70 px-3 py-2">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      <div className="text-sm font-semibold text-foreground">{value}</div>
    </div>
  );
}
