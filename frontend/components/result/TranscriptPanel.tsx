'use client';

import { memo, useState, useMemo } from 'react';
import { Download, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';

interface TranscriptSegment {
  start: number;
  end?: number;
  text: string;
}

interface TranscriptPanelProps {
  segments: TranscriptSegment[];
  videoId?: string;
}

function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return h > 0 ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}` : `${m}:${String(s).padStart(2, '0')}`;
}

function formatSrtTimestamp(seconds: number): string {
  const safe = Math.max(0, seconds);
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = Math.floor(safe % 60);
  const ms = Math.floor((safe % 1) * 1000);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

export function transcriptToSrt(segments: TranscriptSegment[]): string {
  return segments.map((segment, index) => {
    const nextStart = segments[index + 1]?.start;
    const end = segment.end && segment.end > segment.start
      ? segment.end
      : Math.max(segment.start + 2, nextStart ?? segment.start + 5);
    return `${index + 1}\n${formatSrtTimestamp(segment.start)} --> ${formatSrtTimestamp(end)}\n${segment.text.trim()}`;
  }).join('\n\n');
}

function downloadSrt(segments: TranscriptSegment[]) {
  const url = URL.createObjectURL(new Blob([transcriptToSrt(segments)], { type: 'application/x-subrip;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'transcript.srt';
  link.click();
  URL.revokeObjectURL(url);
}

export const TranscriptPanel = memo(function TranscriptPanel({ segments, videoId }: TranscriptPanelProps) {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return segments;
    const q = search.toLowerCase();
    return segments.filter((s) => s.text.toLowerCase().includes(q));
  }, [segments, search]);

  const handleTimestampClick = (seconds: number) => {
    if (videoId) {
      window.open(`https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(seconds)}s`, '_blank');
    }
  };

  if (!segments.length) return null;

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-400" />
          <Input
            placeholder="자막 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-9 text-sm"
          />
        </div>
        <Button type="button" variant="outline" size="sm" className="h-9 gap-1.5" onClick={() => downloadSrt(segments)}>
          <Download className="h-3.5 w-3.5" /> SRT
        </Button>
      </div>
      <ScrollArea className="h-[400px]">
        <div className="space-y-1">
          {filtered.map((seg, i) => (
            <div key={`${seg.start}-${i}`} className="flex gap-2 py-1 px-2 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 group">
              <button
                onClick={() => handleTimestampClick(seg.start)}
                aria-label={`${formatTimestamp(seg.start)} 타임스탬프로 이동`}
                className="text-xs font-mono text-blue-500 hover:text-blue-700 dark:text-blue-400 shrink-0 pt-0.5"
              >
                {formatTimestamp(seg.start)}
              </button>
              <span className="text-sm text-zinc-700 dark:text-zinc-300">{seg.text}</span>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
});

export default TranscriptPanel;
