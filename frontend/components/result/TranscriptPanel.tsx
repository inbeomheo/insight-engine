'use client';

import { memo, useState, useMemo } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';

interface TranscriptSegment {
  start: number;
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
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-400" />
        <Input
          placeholder="자막 검색..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 h-9 text-sm"
        />
      </div>
      <ScrollArea className="h-[400px]">
        <div className="space-y-1">
          {filtered.map((seg, i) => (
            <div key={i} className="flex gap-2 py-1 px-2 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 group">
              <button
                onClick={() => handleTimestampClick(seg.start)}
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
