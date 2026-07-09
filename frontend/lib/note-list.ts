import type { NoteListItem } from './api';
import {
  getNoteStudySummary,
  type NoteStudyCounts,
  type NoteStudyProgress,
  type NoteStudySummary,
} from './note-study-progress';

export type NoteFacet =
  | { type: 'concept'; value: string }
  | { type: 'tag'; value: string }
  | { type: 'source'; value: string };

export function getNoteSourceLabel(type?: string): string {
  if (type === 'youtube') return 'YouTube';
  if (type === 'text') return '직접 텍스트';
  if (type === 'article') return 'Article';
  if (type === 'document') return '문서';
  if (type === 'voice') return '음성';
  return '기타';
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

export function noteMatchesFacet(note: NoteListItem, facet: NoteFacet): boolean {
  const target = normalize(facet.value);
  if (!target) return true;

  if (facet.type === 'concept') {
    return (note.key_concepts ?? []).some((concept) => normalize(concept) === target);
  }
  if (facet.type === 'tag') {
    return (note.tags ?? []).some((tag) => normalize(tag) === target);
  }

  return normalize(getNoteSourceLabel(note.source?.type)) === target;
}

export function filterNotesByFacet(notes: NoteListItem[], facet: NoteFacet | null): NoteListItem[] {
  if (!facet) return notes;
  return notes.filter((note) => noteMatchesFacet(note, facet));
}

export function sortNotesByRecent(notes: NoteListItem[]): NoteListItem[] {
  return [...notes].sort((a, b) => {
    const timeA = Date.parse(a.created_at);
    const timeB = Date.parse(b.created_at);
    return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA);
  });
}

export function getFacetLabel(facet: NoteFacet): string {
  if (facet.type === 'concept') return `개념: ${facet.value}`;
  if (facet.type === 'tag') return `태그: ${facet.value}`;
  return `출처: ${facet.value}`;
}

export interface NoteStudyResumeItem {
  note: NoteListItem;
  summary: NoteStudySummary;
  updatedAt: string | null;
}

export type NoteStudyStatus = 'not-started' | 'in-progress' | 'completed';

export function getNoteStudyCounts(note: NoteListItem): NoteStudyCounts {
  return {
    learning: note.learning_point_count ?? 0,
    review: note.review_question_count ?? 0,
  };
}

export function getNoteStudyStatus(
  note: NoteListItem,
  progress?: NoteStudyProgress
): NoteStudyStatus {
  const summary = getNoteStudySummary(
    progress ?? { learning: [], review: [], updatedAt: null },
    getNoteStudyCounts(note)
  );
  if (summary.total === 0 || summary.completed === 0) return 'not-started';
  if (summary.completed >= summary.total) return 'completed';
  return 'in-progress';
}

export function getNoteStudyStatusLabel(status: NoteStudyStatus): string {
  if (status === 'completed') return '완료';
  if (status === 'in-progress') return '진행중';
  return '미시작';
}

export function getNoteStudyStatusCounts(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>
): Record<NoteStudyStatus, number> {
  return notes.reduce<Record<NoteStudyStatus, number>>(
    (counts, note) => {
      const status = getNoteStudyStatus(note, progressByNote[note.id]);
      counts[status] += 1;
      return counts;
    },
    { 'not-started': 0, 'in-progress': 0, completed: 0 }
  );
}

export function filterNotesByStudyStatus(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  status: NoteStudyStatus | null
): NoteListItem[] {
  if (!status) return notes;
  return notes.filter((note) => getNoteStudyStatus(note, progressByNote[note.id]) === status);
}

export function getNotesWithStudyProgress(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  limit = 3
): NoteStudyResumeItem[] {
  return notes
    .map((note) => {
      const progress = progressByNote[note.id];
      const summary = getNoteStudySummary(
        progress ?? { learning: [], review: [], updatedAt: null },
        getNoteStudyCounts(note)
      );
      return { note, summary, updatedAt: progress?.updatedAt ?? null };
    })
    .filter((item) => item.summary.total > 0 && item.summary.completed > 0)
    .sort((a, b) => {
      const timeA = a.updatedAt ? Date.parse(a.updatedAt) : 0;
      const timeB = b.updatedAt ? Date.parse(b.updatedAt) : 0;
      return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA);
    })
    .slice(0, limit);
}
