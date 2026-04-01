'use client';

import { useEffect, useState } from 'react';
import { Loader2, Check, Wrench } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ToolExecution } from '../hooks/useAgentChat';

function ElapsedTimer({ startedAt }: { startedAt: number }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((Date.now() - startedAt) / 1000);
    }, 100);
    return () => clearInterval(interval);
  }, [startedAt]);

  return <span className="tabular-nums">{elapsed.toFixed(1)}s</span>;
}

interface ToolProgressProps {
  tools: ToolExecution[];
}

export default function ToolProgress({ tools }: ToolProgressProps) {
  if (!tools.length) return null;

  return (
    <div className="flex flex-col gap-1.5 my-2">
      {tools.map((tool, i) => (
        <div
          key={`${tool.name}-${i}`}
          className={cn(
            'flex items-center gap-2 text-xs px-3 py-1.5 rounded-md',
            'bg-muted/50 dark:bg-muted/30 border border-border/50',
            tool.done && 'opacity-70',
          )}
        >
          {tool.done ? (
            <Check className="size-3.5 text-emerald-500 shrink-0" />
          ) : (
            <Loader2 className="size-3.5 animate-spin text-primary shrink-0" />
          )}
          <Wrench className="size-3 text-muted-foreground shrink-0" />
          <span className="font-mono text-foreground/80 truncate">{tool.name}</span>
          <span className="ml-auto text-muted-foreground shrink-0">
            {tool.done && tool.elapsed != null ? (
              `${tool.elapsed.toFixed(1)}s`
            ) : (
              <ElapsedTimer startedAt={tool.startedAt} />
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
