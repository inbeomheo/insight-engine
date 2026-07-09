import { describe, expect, it } from 'vitest';
import type { NoteListItem } from './api';
import {
  filterNotesByFacet,
  getFacetLabel,
  getNoteSourceLabel,
  sortNotesByRecent,
} from './note-list';

function note(input: Partial<NoteListItem> & { id: string }): NoteListItem {
  return {
    ...input,
    id: input.id,
    title: input.title ?? input.id,
    tags: input.tags ?? [],
    key_concepts: input.key_concepts ?? [],
    created_at: input.created_at ?? '2026-07-10T00:00:00Z',
    source: input.source ?? { type: 'text', url: '', title: '직접 텍스트' },
  };
}

describe('note-list', () => {
  const notes = [
    note({
      id: 'rag',
      tags: ['AI', '검색'],
      key_concepts: ['RAG', 'ChromaDB'],
      created_at: '2026-07-10T03:00:00Z',
      source: { type: 'youtube', url: 'https://youtu.be/a', title: '영상' },
    }),
    note({
      id: 'memo',
      tags: ['학습'],
      key_concepts: ['복습'],
      created_at: '2026-07-10T01:00:00Z',
      source: { type: 'text', url: '', title: '메모' },
    }),
  ];

  it('labels common note source types', () => {
    expect(getNoteSourceLabel('youtube')).toBe('YouTube');
    expect(getNoteSourceLabel('text')).toBe('직접 텍스트');
    expect(getNoteSourceLabel('unknown')).toBe('기타');
  });

  it('filters notes by concept, tag, and source facets', () => {
    expect(filterNotesByFacet(notes, { type: 'concept', value: 'rag' }).map((n) => n.id)).toEqual(['rag']);
    expect(filterNotesByFacet(notes, { type: 'tag', value: '학습' }).map((n) => n.id)).toEqual(['memo']);
    expect(filterNotesByFacet(notes, { type: 'source', value: 'YouTube' }).map((n) => n.id)).toEqual(['rag']);
    expect(filterNotesByFacet(notes, null)).toHaveLength(2);
  });

  it('sorts notes by recent created date first', () => {
    expect(sortNotesByRecent([notes[1], notes[0]]).map((n) => n.id)).toEqual(['rag', 'memo']);
  });

  it('builds readable active facet labels', () => {
    expect(getFacetLabel({ type: 'tag', value: 'AI' })).toBe('태그: AI');
  });
});
