import type { NoteListItem } from './api';

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
