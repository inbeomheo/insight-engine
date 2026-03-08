'use client';
import { memo } from 'react';

interface Chapter {
  title: string;
  start: number;
  end: number;
  summary: string;
}

interface ChapterTimelineProps {
  chapters: Chapter[];
  videoUrl?: string;
}

// 초 -> MM:SS 포맷
function fmtTime(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

export const ChapterTimeline = memo(function ChapterTimeline({ chapters, videoUrl }: ChapterTimelineProps) {
  if (!chapters.length) return null;
  const total = chapters[chapters.length - 1].end || 1;

  function handleClick(start: number) {
    if (!videoUrl) return;
    const sep = videoUrl.includes('?') ? '&' : '?';
    window.open(`${videoUrl}${sep}t=${Math.floor(start)}s`, '_blank');
  }

  return (
    <div className="mt-5 space-y-3">
      <h4 className="text-sm font-medium flex items-center gap-2">
        챕터 ({chapters.length})
      </h4>
      {/* 타임라인 바 */}
      <div className="flex h-2 rounded-full overflow-hidden bg-zinc-200 dark:bg-zinc-700">
        {chapters.map((ch, i) => {
          const width = ((ch.end - ch.start) / total) * 100;
          const colors = ['bg-blue-500', 'bg-emerald-500', 'bg-amber-500', 'bg-purple-500', 'bg-rose-500', 'bg-cyan-500', 'bg-indigo-500', 'bg-teal-500'];
          return (
            <button
              key={i}
              onClick={() => handleClick(ch.start)}
              aria-label={`${ch.title} 챕터 (${fmtTime(ch.start)})`}
              className={`${colors[i % colors.length]} hover:opacity-80 transition-opacity cursor-pointer`}
              style={{ width: `${width}%` }}
              title={`${ch.title} (${fmtTime(ch.start)})`}
            />
          );
        })}
      </div>
      {/* 챕터 카드 */}
      <div className="grid gap-2 grid-cols-1 sm:grid-cols-2">
        {chapters.map((ch, i) => (
          <button
            key={i}
            onClick={() => handleClick(ch.start)}
            aria-label={`${ch.title} 챕터로 이동`}
            className="text-left p-3 rounded-lg border border-zinc-200 dark:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-blue-500">{fmtTime(ch.start)}</span>
              <span className="text-sm font-medium truncate">{ch.title}</span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2">{ch.summary}</p>
          </button>
        ))}
      </div>
    </div>
  );
});

export default ChapterTimeline;
