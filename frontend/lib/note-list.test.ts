import { describe, expect, it } from 'vitest';
import type { NoteListItem } from './api';
import {
  filterNotesByStudyStatus,
  filterNotesByFacet,
  getFacetLabel,
  getNotesWithStudyProgress,
  getNoteSourceLabel,
  getNoteStudyCounts,
  getNoteStudyStatus,
  getNoteStudyStatusCounts,
  getNoteStudyStatusLabel,
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

  it('builds study resume items from local progress', () => {
    const source = note({
      id: 'study',
      learning_point_count: 3,
      review_question_count: 2,
      created_at: '2026-07-10T02:00:00Z',
    });
    const stale = note({
      id: 'stale',
      learning_point_count: 1,
      review_question_count: 0,
      created_at: '2026-07-10T03:00:00Z',
    });

    expect(getNoteStudyCounts(source)).toEqual({ learning: 3, review: 2 });
    expect(
      getNotesWithStudyProgress([source, stale], {
        study: { learning: [0, 2], review: [1], updatedAt: '2026-07-10T05:00:00Z' },
        stale: { learning: [], review: [], updatedAt: '2026-07-10T06:00:00Z' },
      })
    ).toEqual([
      {
        note: source,
        summary: {
          completed: 3,
          total: 5,
          percent: 60,
          completedLearning: 2,
          completedReview: 1,
        },
        updatedAt: '2026-07-10T05:00:00Z',
      },
    ]);
  });

  it('classifies and filters notes by study status', () => {
    const pending = note({ id: 'pending', learning_point_count: 2, review_question_count: 1 });
    const ongoing = note({ id: 'ongoing', learning_point_count: 2, review_question_count: 1 });
    const done = note({ id: 'done', learning_point_count: 1, review_question_count: 1 });
    const progress = {
      ongoing: { learning: [0], review: [], updatedAt: '2026-07-10T01:00:00Z' },
      done: { learning: [0], review: [0], updatedAt: '2026-07-10T02:00:00Z' },
    };

    expect(getNoteStudyStatus(pending)).toBe('not-started');
    expect(getNoteStudyStatus(ongoing, progress.ongoing)).toBe('in-progress');
    expect(getNoteStudyStatus(done, progress.done)).toBe('completed');
    expect(getNoteStudyStatusLabel('in-progress')).toBe('진행중');
    expect(getNoteStudyStatusCounts([pending, ongoing, done], progress)).toEqual({
      'not-started': 1,
      'in-progress': 1,
      completed: 1,
    });
    expect(filterNotesByStudyStatus([pending, ongoing, done], progress, 'completed').map((n) => n.id)).toEqual(['done']);
  });
});
