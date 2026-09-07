'use client';

import Link from 'next/link';
import { Link2 } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { getNoteBacklinks, type NoteBacklink } from '@/lib/note-graph';

export function NoteBacklinksPanel() {
  const pathname = usePathname();
  const noteId = useMemo(() => {
    if (pathname === '/notes/graph') return null;
    const match = pathname.match(/^\/notes\/([^/]+)$/);
    return match ? decodeURIComponent(match[1]) : null;
  }, [pathname]);
  const [notes, setNotes] = useState<NoteBacklink[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!noteId) {
      setNotes([]);
      setError(null);
      setLoading(false);
      return;
    }

    let alive = true;
    setLoading(true);
    setError(null);
    getNoteBacklinks(noteId)
      .then((result) => {
        if (alive) setNotes(result.notes);
      })
      .catch((err) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : '역방향 연결을 불러오지 못했습니다.');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [noteId]);

  if (!noteId) return null;

  return (
    <aside className="mx-auto w-full max-w-4xl px-4 pb-10 sm:px-6" aria-labelledby="note-backlinks-title">
      <div className="rounded-2xl border bg-card p-5">
        <div className="flex items-center gap-2">
          <Link2 className="h-4 w-4 text-muted-foreground" />
          <h2 id="note-backlinks-title" className="font-semibold">이 노트를 연결한 노트</h2>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          다른 노트의 상위 유사도 연결을 역방향으로 모았습니다.
        </p>

        {loading ? <p className="mt-4 text-sm text-muted-foreground">연결을 찾는 중…</p> : null}
        {error ? <p role="alert" className="mt-4 text-sm text-destructive">{error}</p> : null}
        {!loading && !error && notes.length === 0 ? (
          <p className="mt-4 text-sm text-muted-foreground">아직 이 노트를 가리키는 연결이 없습니다.</p>
        ) : null}
        {!loading && !error && notes.length > 0 ? (
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {notes.map((note) => (
              <li key={note.id}>
                <Link
                  href={`/notes/${encodeURIComponent(note.id)}`}
                  className="flex min-h-12 items-center justify-between gap-3 rounded-xl bg-muted/45 px-3 py-2 text-sm hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="min-w-0 truncate font-medium">{note.title}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {Math.round(note.score * 100)}%
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </aside>
  );
}
