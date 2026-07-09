import { describe, expect, it } from 'vitest';
import { buildNoteOutline } from './note-outline';

describe('buildNoteOutline', () => {
  it('builds a wiki-style outline with only available sections', () => {
    const outline = buildNoteOutline(
      {
        key_concepts: ['RAG', '인용'],
        learning_points: ['출처를 확인한다'],
        review_questions: [{ question: '왜?', answer: '근거 확인' }],
        summary: '요약',
        quotes: [{ text: '근거', ref: '1' }],
        related_notes: [{ id: 'n2' }],
      },
      { hasLinkedReport: true }
    );

    expect(outline).toEqual([
      { id: 'source', label: '출처' },
      { id: 'source-result', label: '원본 결과' },
      { id: 'study-progress', label: '복습 진행', count: 2 },
      { id: 'concepts', label: '핵심 개념', count: 2 },
      { id: 'learning-points', label: '학습 포인트', count: 1 },
      { id: 'review-questions', label: '복습 질문', count: 1 },
      { id: 'summary', label: '요약' },
      { id: 'chat', label: '근거 Q&A' },
      { id: 'related-notes', label: '관련 노트', count: 1 },
      { id: 'quotes', label: '근거 인용', count: 1 },
    ]);
  });

  it('keeps source and chat while omitting empty sections', () => {
    expect(
      buildNoteOutline({
        key_concepts: [],
        learning_points: [],
        review_questions: [],
        summary: '   ',
        quotes: [],
        related_notes: [],
      })
    ).toEqual([
      { id: 'source', label: '출처' },
      { id: 'chat', label: '근거 Q&A' },
    ]);
  });
});
