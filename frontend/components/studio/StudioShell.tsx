'use client';

import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface StudioShellProps extends HTMLAttributes<HTMLDivElement> {
  sidebar: ReactNode;
  header: ReactNode;
  main: ReactNode;
  rightPanel: ReactNode;
}

export default function StudioShell({ sidebar, header, main, rightPanel, className, ...rootProps }: StudioShellProps) {
  return (
    <div
      className={cn('min-h-screen bg-[radial-gradient(circle_at_top_left,#eef2ff_0,#f6f7fb_34%,#f8fafc_100%)] text-foreground', className)}
      {...rootProps}
    >
      <div className="flex h-screen overflow-hidden">
        {sidebar}
        <div className="flex min-w-0 flex-1 flex-col">
          {header}
          <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px]">
            <main id="main-content" className="min-w-0 overflow-y-auto px-4 py-5 sm:px-6 lg:px-8" role="main">
              <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">{main}</div>
            </main>
            <aside className="hidden min-h-0 border-l border-slate-200/70 bg-white/70 backdrop-blur-xl xl:block">{rightPanel}</aside>
          </div>
        </div>
      </div>
    </div>
  );
}
