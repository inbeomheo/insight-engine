'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, ExternalLink, Quote } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { getNote, type NoteDetail } from '@/lib/api';

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

export default function NoteDetailPage() {
  const params = useParams<{ id: string }>();
  const noteId = params.id;
  const [note, setNote] = useState<NoteDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          <NoteBody note={note} />
        ) : null}
      </div>
    </div>
  );
}

function NoteBody({ note }: { note: NoteDetail }) {
  const sourceUrl = note.source?.url ? safeHttpUrl(note.source.url) : null;
  return (
    <div className="space-y-6">
      {/* 헤더: 제목 + 출처 */}
      <div>
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

      {/* 인용구 */}
      {note.quotes.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-foreground mb-2.5">인용</h2>
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
