import { describe, expect, it } from 'vitest';
import type { NoteListItem } from './api';
import {
  buildDailyStudyPlanMarkdown,
  buildNoteFacetHref,
  buildWikiIndexMarkdown,
  filterNotesByStudyStatus,
  filterNotesByFacet,
  getCompletedStudyItems,
  getDailyStudyPlanItems,
  getFacetLabel,
  getKnowledgeGapConcepts,
  getNoteConceptClusters,
  getNoteStudyCardOrder,
  getNoteStudyQueueCount,
  getNotesNeedingReview,
  getNotesWithStudyProgress,
  getNoteSourceLabel,
  getNoteStudyCounts,
  getNoteStudyStatus,
  getNoteStudyStatusCounts,
  getNoteStudyStatusLabel,
  getRecentStudyResumeItems,
  getStudyStartCandidates,
  parseNotePanelOpen,
  parseNoteFacetSearchParams,
  parseNoteStudyQueueOpen,
  serializeNotePanelOpen,
  serializeNoteStudyQueueOpen,
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

  it('builds and parses wiki facet deep links', () => {
    expect(buildNoteFacetHref({ type: 'concept', value: 'RAG 검색' })).toBe('/notes?concept=RAG+%EA%B2%80%EC%83%89');
    expect(parseNoteFacetSearchParams(new URLSearchParams('concept=RAG&tag=AI'))).toEqual({
      type: 'concept',
      value: 'RAG',
    });
    expect(parseNoteFacetSearchParams(new URLSearchParams('tag=%ED%95%99%EC%8A%B5'))).toEqual({
      type: 'tag',
      value: '학습',
    });
    expect(parseNoteFacetSearchParams(new URLSearchParams('source=YouTube'))).toEqual({
      type: 'source',
      value: 'YouTube',
    });
    expect(parseNoteFacetSearchParams(new URLSearchParams('concept=   '))).toBeNull();
  });

  it('sorts notes by recent created date first', () => {
    expect(sortNotesByRecent([notes[1], notes[0]]).map((n) => n.id)).toEqual(['rag', 'memo']);
  });

  it('builds wiki concept clusters with recent linked notes', () => {
    const recent = note({
      id: 'recent-rag',
      key_concepts: ['RAG', 'RAG', 'Vector DB'],
      created_at: '2026-07-10T05:00:00Z',
    });
    const older = note({
      id: 'older-rag',
      key_concepts: ['rag'],
      created_at: '2026-07-10T01:00:00Z',
    });
    const singleton = note({
      id: 'solo',
      key_concepts: ['Only Once'],
      created_at: '2026-07-10T06:00:00Z',
    });
    const vector = note({
      id: 'vector',
      key_concepts: ['Vector DB'],
      created_at: '2026-07-10T04:00:00Z',
    });

    expect(
      getNoteConceptClusters([older, singleton, vector, recent], {
        limit: 2,
        notesPerCluster: 1,
      })
    ).toEqual([
      { concept: 'RAG', count: 2, notes: [recent] },
      { concept: 'Vector DB', count: 2, notes: [recent] },
    ]);
  });

  it('finds recent concepts that only appear in one note', () => {
    const recent = note({
      id: 'recent-gap',
      title: 'Recent gap',
      key_concepts: ['Solo', 'RAG', 'solo'],
      created_at: '2026-07-10T05:00:00Z',
    });
    const older = note({
      id: 'older-gap',
      title: 'Older gap',
      key_concepts: ['Legacy', 'RAG'],
      created_at: '2026-07-10T01:00:00Z',
    });

    expect(getKnowledgeGapConcepts([older, recent], 2)).toEqual([
      { concept: 'Solo', note: recent },
      { concept: 'Legacy', note: older },
    ]);
    expect(getKnowledgeGapConcepts([older, recent], 0)).toEqual([]);
  });

  it('builds markdown for the wiki concept index', () => {
    const recent = note({
      id: 'recent rag',
      title: '  최신\n[RAG]  ',
      key_concepts: ['RAG'],
      created_at: '2026-07-10T05:00:00Z',
    });
    const older = note({
      id: 'older-rag',
      title: '',
      key_concepts: ['rag'],
      created_at: '2026-07-10T01:00:00Z',
    });
    const clusters = getNoteConceptClusters([older, recent], { notesPerCluster: 2 });

    expect(buildWikiIndexMarkdown(clusters, '  개념\n지도  ')).toBe([
      '# 개념 지도',
      '',
      '1. RAG (2개 문서)',
      '   - [최신 \\[RAG\\]](/notes/recent%20rag)',
      '   - [제목 없음](/notes/older-rag)',
    ].join('\n'));

    expect(buildWikiIndexMarkdown([], '')).toBe('# 위키 인덱스\n\n묶을 수 있는 반복 개념이 없습니다.');
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

  it('prioritizes unfinished study notes that need review', () => {
    const lowOld = note({ id: 'low-old', learning_point_count: 4, review_question_count: 0 });
    const lowNew = note({ id: 'low-new', learning_point_count: 4, review_question_count: 0 });
    const high = note({ id: 'high', learning_point_count: 4, review_question_count: 0 });
    const done = note({ id: 'done-review', learning_point_count: 2, review_question_count: 0 });
    const fresh = note({ id: 'fresh', learning_point_count: 3, review_question_count: 0 });

    expect(
      getNotesNeedingReview([high, done, lowOld, fresh, lowNew], {
        high: { learning: [0, 1, 2], review: [], updatedAt: '2026-07-10T07:00:00Z' },
        'done-review': { learning: [0, 1], review: [], updatedAt: '2026-07-10T08:00:00Z' },
        'low-old': { learning: [0], review: [], updatedAt: '2026-07-10T04:00:00Z' },
        fresh: { learning: [], review: [], updatedAt: '2026-07-10T09:00:00Z' },
        'low-new': { learning: [0], review: [], updatedAt: '2026-07-10T06:00:00Z' },
      }).map((item) => item.note.id)
    ).toEqual(['low-new', 'low-old', 'high']);
  });

  it('builds recent resume items without duplicated priority review notes', () => {
    const priority = note({ id: 'priority', learning_point_count: 4, review_question_count: 0 });
    const recentDone = note({ id: 'recent-done', learning_point_count: 2, review_question_count: 0 });
    const older = note({ id: 'older', learning_point_count: 2, review_question_count: 0 });
    const backfill = note({ id: 'backfill', learning_point_count: 2, review_question_count: 0 });

    expect(
      getRecentStudyResumeItems(
        [older, priority, backfill, recentDone],
        {
          priority: { learning: [0], review: [], updatedAt: '2026-07-10T09:00:00Z' },
          'recent-done': { learning: [0, 1], review: [], updatedAt: '2026-07-10T08:00:00Z' },
          older: { learning: [0], review: [], updatedAt: '2026-07-10T07:00:00Z' },
          backfill: { learning: [0], review: [], updatedAt: '2026-07-10T06:00:00Z' },
        },
        new Set(['priority']),
        3
      ).map((item) => item.note.id)
    ).toEqual(['recent-done', 'older', 'backfill']);
  });

  it('recommends recent not-started notes as study start candidates', () => {
    const newer = note({
      id: 'newer',
      learning_point_count: 1,
      review_question_count: 1,
      created_at: '2026-07-10T09:00:00Z',
    });
    const older = note({
      id: 'older-start',
      learning_point_count: 2,
      review_question_count: 0,
      created_at: '2026-07-10T07:00:00Z',
    });
    const started = note({
      id: 'started',
      learning_point_count: 2,
      review_question_count: 0,
      created_at: '2026-07-10T10:00:00Z',
    });
    const empty = note({
      id: 'empty',
      learning_point_count: 0,
      review_question_count: 0,
      created_at: '2026-07-10T11:00:00Z',
    });

    expect(
      getStudyStartCandidates(
        [empty, started, older, newer],
        {
          started: { learning: [0], review: [], updatedAt: '2026-07-10T10:30:00Z' },
        },
        2
      ).map((item) => item.note.id)
    ).toEqual(['newer', 'older-start']);
  });

  it('builds completed study items by latest update time', () => {
    const recentDone = note({ id: 'recent-complete', learning_point_count: 1, review_question_count: 1 });
    const olderDone = note({ id: 'older-complete', learning_point_count: 2, review_question_count: 0 });
    const ongoing = note({ id: 'ongoing-complete-test', learning_point_count: 2, review_question_count: 0 });
    const empty = note({ id: 'empty-complete-test', learning_point_count: 0, review_question_count: 0 });

    expect(
      getCompletedStudyItems(
        [ongoing, olderDone, empty, recentDone],
        {
          'recent-complete': { learning: [0], review: [0], updatedAt: '2026-07-10T10:00:00Z' },
          'older-complete': { learning: [0, 1], review: [], updatedAt: '2026-07-10T08:00:00Z' },
          'ongoing-complete-test': { learning: [0], review: [], updatedAt: '2026-07-10T11:00:00Z' },
        },
        2
      ).map((item) => item.note.id)
    ).toEqual(['recent-complete', 'older-complete']);
  });

  it('builds a daily study plan from unfinished and not-started notes', () => {
    const low = note({ id: 'low-plan', learning_point_count: 4, review_question_count: 0 });
    const high = note({ id: 'high-plan', learning_point_count: 4, review_question_count: 0 });
    const start = note({
      id: 'start-plan',
      learning_point_count: 1,
      review_question_count: 1,
      created_at: '2026-07-10T09:00:00Z',
    });
    const done = note({ id: 'done-plan', learning_point_count: 1, review_question_count: 0 });
    const empty = note({ id: 'empty-plan', learning_point_count: 0, review_question_count: 0 });

    expect(
      getDailyStudyPlanItems(
        [done, start, high, empty, low],
        {
          'low-plan': { learning: [0], review: [], updatedAt: '2026-07-10T05:00:00Z' },
          'high-plan': { learning: [0, 1, 2], review: [], updatedAt: '2026-07-10T06:00:00Z' },
          'done-plan': { learning: [0], review: [], updatedAt: '2026-07-10T07:00:00Z' },
        },
        3
      ).map((item) => ({
        id: item.note.id,
        kind: item.kind,
        remaining: item.remaining,
        label: item.label,
      }))
    ).toEqual([
      { id: 'low-plan', kind: 'continue', remaining: 3, label: '이어 복습' },
      { id: 'high-plan', kind: 'continue', remaining: 1, label: '이어 복습' },
      { id: 'start-plan', kind: 'start', remaining: 2, label: '새로 시작' },
    ]);
  });

  it('builds markdown for the daily study plan', () => {
    const plan = getDailyStudyPlanItems(
      [
        note({ id: 'continue plan', title: '이어갈 노트', learning_point_count: 3, review_question_count: 0 }),
        note({ id: 'start-plan', title: '  새\n노트  ', learning_point_count: 1, review_question_count: 1 }),
      ],
      {
        'continue plan': { learning: [0], review: [], updatedAt: '2026-07-10T05:00:00Z' },
      },
      2
    );

    expect(buildDailyStudyPlanMarkdown(plan, '  오늘\n계획  ')).toBe([
      '# 오늘 계획',
      '',
      '1. 이어갈 노트',
      '   - 단계: 이어 복습',
      '   - 행동: 남은 항목 이어가기',
      '   - 남은 항목: 2개',
      '   - 진행: 1/3 (33%)',
      '   - 링크: /notes/continue%20plan#study-progress',
      '2. 새 노트',
      '   - 단계: 새로 시작',
      '   - 행동: 첫 체크 시작',
      '   - 남은 항목: 2개',
      '   - 진행: 0/2 (0%)',
      '   - 링크: /notes/start-plan#study-progress',
    ].join('\n'));

    expect(buildDailyStudyPlanMarkdown([], '')).toBe('# 오늘의 복습 플랜\n\n복습할 노트가 없습니다.');
  });

  it('orders study dashboard cards by action priority', () => {
    expect(getNoteStudyCardOrder({
      'study-start': 2,
      'review-needed': 1,
      completed: 3,
      recent: 4,
    })).toEqual(['review-needed', 'study-start', 'completed', 'recent']);
    expect(getNoteStudyCardOrder({
      'study-start': 0,
      'review-needed': 2,
      completed: 0,
      recent: 1,
    })).toEqual(['review-needed', 'recent']);
  });

  it('counts visible study queue items only', () => {
    expect(getNoteStudyQueueCount({
      'study-start': 0,
      'review-needed': 2,
      completed: 0,
      recent: 1,
    })).toBe(3);
  });

  it('serializes study queue open state for browser storage', () => {
    expect(serializeNotePanelOpen(true)).toBe('open');
    expect(serializeNotePanelOpen(false)).toBe('closed');
    expect(parseNotePanelOpen('open')).toBe(true);
    expect(parseNotePanelOpen('closed')).toBe(false);
    expect(parseNotePanelOpen('legacy', false)).toBe(false);
    expect(serializeNoteStudyQueueOpen(true)).toBe('open');
    expect(serializeNoteStudyQueueOpen(false)).toBe('closed');
    expect(parseNoteStudyQueueOpen('open')).toBe(true);
    expect(parseNoteStudyQueueOpen('closed')).toBe(false);
    expect(parseNoteStudyQueueOpen('legacy', false)).toBe(false);
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
