import { describe, expect, it } from 'vitest';
import { createNoteRecallRetryState, getNoteRecallRetrySummary, normalizeNoteRecallRetryState, toggleNoteRecallRetryItem } from './note-recall-retry';

describe('note recall retry state', () => {
  it('creates an empty one-off session', () => {
    const state = createNoteRecallRetryState(2);
    expect(state).toEqual({ completedIndexes: [] });
    expect(getNoteRecallRetrySummary(state, 2)).toEqual({ completed: 0, total: 2, isComplete: false });
  });

  it('normalizes and toggles only valid indexes', () => {
    const state = normalizeNoteRecallRetryState({ completedIndexes: [1, 1, 3, -1, 0] }, 2);
    expect(state).toEqual({ completedIndexes: [0, 1] });
    expect(toggleNoteRecallRetryItem(state, 0, 2)).toEqual({ completedIndexes: [1] });
    expect(toggleNoteRecallRetryItem(state, 4, 2)).toEqual(state);
  });

  it('keeps a zero-question session incomplete', () => {
    expect(getNoteRecallRetrySummary(createNoteRecallRetryState(0), 0)).toEqual({ completed: 0, total: 0, isComplete: false });
  });
});
