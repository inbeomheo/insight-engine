import type { ReactNode } from 'react';

import { NoteBacklinksPanel } from '@/components/note-backlinks-panel';
import { NotesViewTabs } from '@/components/notes-view-tabs';

export default function NotesLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <NotesViewTabs />
      {children}
      <NoteBacklinksPanel />
    </>
  );
}
