'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { Network } from 'lucide-react';

import {
  buildCircularGraphLayout,
  connectedNodeIds,
  type NoteGraphResponse,
} from '@/lib/note-graph';

export function NoteRelationGraph({ graph }: { graph: NoteGraphResponse }) {
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const points = useMemo(() => buildCircularGraphLayout(graph.nodes), [graph.nodes]);
  const pointById = useMemo(
    () => new Map(points.map((point) => [point.id, point])),
    [points],
  );
  const connected = useMemo(
    () => (focusedId ? connectedNodeIds(focusedId, graph.edges) : null),
    [focusedId, graph.edges],
  );

  if (points.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed p-10 text-center text-sm text-muted-foreground">
        아직 그래프로 표시할 노트가 없습니다.
      </div>
    );
  }

  return (
    <section aria-label="지식 노트 관계 그래프" className="space-y-5">
      <div
        className="relative min-h-[430px] overflow-hidden rounded-3xl border bg-muted/20 sm:min-h-[560px]"
        onMouseLeave={() => setFocusedId(null)}
      >
        <svg
          aria-hidden="true"
          className="absolute inset-0 h-full w-full"
          preserveAspectRatio="none"
          viewBox="0 0 100 100"
        >
          {graph.edges.map((edge) => {
            const source = pointById.get(edge.source);
            const target = pointById.get(edge.target);
            if (!source || !target) return null;
            const isActive = !focusedId || edge.source === focusedId || edge.target === focusedId;
            return (
              <line
                key={`${edge.source}:${edge.target}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                vectorEffect="non-scaling-stroke"
                className={isActive ? 'stroke-foreground/35' : 'stroke-foreground/10'}
                strokeWidth={isActive ? 1.4 : 0.8}
              />
            );
          })}
        </svg>

        {points.map((point) => {
          const isDimmed = Boolean(connected && !connected.has(point.id));
          return (
            <Link
              key={point.id}
              href={`/notes/${encodeURIComponent(point.id)}`}
              onFocus={() => setFocusedId(point.id)}
              onBlur={() => setFocusedId(null)}
              onMouseEnter={() => setFocusedId(point.id)}
              className={[
                'absolute z-10 w-24 -translate-x-1/2 -translate-y-1/2 rounded-2xl border bg-background/95 px-3 py-2 text-center shadow-sm transition sm:w-32',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                isDimmed ? 'opacity-30' : 'opacity-100',
              ].join(' ')}
              style={{ left: `${point.x}%`, top: `${point.y}%` }}
              aria-label={`${point.title} 노트 열기`}
            >
              <span className="block truncate text-xs font-semibold sm:text-sm">{point.title}</span>
              {point.key_concepts[0] ? (
                <span className="mt-1 block truncate text-[10px] text-muted-foreground sm:text-xs">
                  {point.key_concepts[0]}
                </span>
              ) : null}
            </Link>
          );
        })}

        <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full border bg-background/90 px-3 py-1.5 text-xs text-muted-foreground">
          <Network className="h-3.5 w-3.5" />
          노드 {graph.meta.node_count} · 연결 {graph.meta.edge_count}
        </div>
      </div>

      <div className="rounded-2xl border bg-card p-4">
        <h2 className="text-sm font-semibold">접근 가능한 관계 목록</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          그래프를 보지 않아도 같은 연결을 목록과 키보드로 탐색할 수 있습니다.
        </p>
        {graph.edges.length === 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">
            현재 임계값을 넘는 노트 관계가 없습니다.
          </p>
        ) : (
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {graph.edges.map((edge) => {
              const source = pointById.get(edge.source);
              const target = pointById.get(edge.target);
              if (!source || !target) return null;
              return (
                <li key={`list:${edge.source}:${edge.target}`} className="rounded-xl bg-muted/40 p-3 text-sm">
                  <Link className="font-medium underline-offset-4 hover:underline" href={`/notes/${encodeURIComponent(source.id)}`}>
                    {source.title}
                  </Link>
                  <span className="mx-2 text-muted-foreground" aria-hidden="true">→</span>
                  <Link className="font-medium underline-offset-4 hover:underline" href={`/notes/${encodeURIComponent(target.id)}`}>
                    {target.title}
                  </Link>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {Math.round(edge.score * 100)}%
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
