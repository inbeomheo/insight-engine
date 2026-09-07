'use client';

import Link from 'next/link';
import { List, Network } from 'lucide-react';
import { usePathname } from 'next/navigation';

export function NotesViewTabs() {
  const pathname = usePathname();
  if (pathname !== '/notes' && pathname !== '/notes/graph') return null;

  const items = [
    { href: '/notes', label: '목록', icon: List },
    { href: '/notes/graph', label: '관계 그래프', icon: Network },
  ];

  return (
    <nav
      aria-label="노트 보기 방식"
      className="mx-auto flex w-full max-w-6xl gap-2 px-4 pt-5 sm:px-6"
    >
      {items.map((item) => {
        const active = pathname === item.href;
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={[
              'inline-flex min-h-10 items-center gap-2 rounded-full border px-4 text-sm font-medium transition',
              active
                ? 'border-foreground/20 bg-foreground text-background'
                : 'bg-background hover:bg-muted',
            ].join(' ')}
          >
            <Icon className="h-4 w-4" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
