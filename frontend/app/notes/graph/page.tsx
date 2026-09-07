'use client';

import { useEffect, useState } from 'react';
import { Network, RefreshCw } from 'lucide-react';

import { NoteRelationGraph } from '@/components/note-relation-graph';
import { Button } from '@/components/ui/button';
import { getNoteGraph, type NoteGraphResponse } from '@/lib/note-graph';
import { useAuthUserId } from '@/hooks/useAuthUserId';

export default function NoteGraphPage() {
  const authUserId = useAuthUserId();
  return <AccountNoteGraphPage key={authUserId ? `user:${authUserId}` : 'anonymous'} />;
}

function AccountNoteGraphPage() {
  const [graph, setGraph] = useState<NoteGraphResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let alive = true;
    getNoteGraph()
      .then((result) => {
        if (alive) setGraph(result);
      })
      .catch((err) => {
        if (!alive) return;
        setGraph(null);
        setError(err instanceof Error ? err.message : '관계 그래프를 불러오지 못했습니다.');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [reloadKey]);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
            <Network className="h-4 w-4" />
            Knowledge map
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">지식 노트 관계 그래프</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            최근 노트와 서로 비슷한 내용을 한눈에 살펴보세요.
            노드를 선택하면 기존 노트 상세로 이동합니다.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setLoading(true);
            setError(null);
            setReloadKey((value) => value + 1);
          }}
          disabled={loading}
        >
          <RefreshCw className="h-4 w-4" />
          새로고침
        </Button>
      </header>

      {loading ? (
        <div className="min-h-[430px] animate-pulse rounded-3xl border bg-muted/30 sm:min-h-[560px]" aria-label="그래프 불러오는 중" />
      ) : null}
      {error ? (
        <div role="alert" className="rounded-2xl border border-destructive/30 bg-destructive/5 p-5 text-sm text-destructive">
          {error}
        </div>
      ) : null}
      {!loading && !error && graph ? <NoteRelationGraph graph={graph} /> : null}
    </main>
  );
}
