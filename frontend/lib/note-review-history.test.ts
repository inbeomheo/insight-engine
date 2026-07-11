import { describe, expect, it } from 'vitest';
import {
  NOTE_REVIEW_HISTORY_STORAGE_KEY,
  getNoteReviewHistorySummary,
  normalizeNoteReviewHistory,
  readNoteReviewHistory,
  recordNoteReviewCompletion,
} from './note-review-history';

function createMemoryStorage() {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => data.set(key, value),
  };
}

describe('note-review-history', () => {
  it('normalizes malformed entries and keeps the latest review per note and day', () => {
    const history = normalizeNoteReviewHistory([
      null,
      { noteId: '', completedAt: 'bad', intervalDays: 0 },
      { noteId: 'note-1', noteTitle: '', completedAt: '2026-07-11T01:00:00.000Z', intervalDays: 1 },
      { noteId: 'note-1', noteTitle: '최신 제목', completedAt: '2026-07-11T08:00:00.000Z', intervalDays: 3 },
    ]);

    expect(history).toEqual([{
      id: 'note-1:2026-07-11',
      noteId: 'note-1',
      noteTitle: '최신 제목',
      completedAt: '2026-07-11T08:00:00.000Z',
      intervalDays: 3,
    }]);
  });

  it('records one completion per note and local day', () => {
    const storage = createMemoryStorage();
    recordNoteReviewCompletion(
      { noteId: 'note-1', noteTitle: '첫 노트', intervalDays: 1 },
      storage,
      new Date('2026-07-11T01:00:00.000Z')
    );
    const updated = recordNoteReviewCompletion(
      { noteId: 'note-1', noteTitle: '첫 노트', intervalDays: 7 },
      storage,
      new Date('2026-07-11T08:00:00.000Z')
    );

    expect(updated).toHaveLength(1);
    expect(updated[0].intervalDays).toBe(7);
    expect(storage.getItem(NOTE_REVIEW_HISTORY_STORAGE_KEY)).toContain('note-1');
    expect(readNoteReviewHistory(storage)).toEqual(updated);
  });

  it('summarizes seven-day activity and a streak ending today or yesterday', () => {
    const entries = normalizeNoteReviewHistory([
      { noteId: 'a', noteTitle: 'A', completedAt: '2026-07-11T08:00:00.000Z', intervalDays: 1 },
      { noteId: 'b', noteTitle: 'B', completedAt: '2026-07-10T08:00:00.000Z', intervalDays: 3 },
      { noteId: 'c', noteTitle: 'C', completedAt: '2026-07-10T09:00:00.000Z', intervalDays: 7 },
      { noteId: 'd', noteTitle: 'D', completedAt: '2026-07-08T08:00:00.000Z', intervalDays: 1 },
      { noteId: 'old', noteTitle: 'Old', completedAt: '2026-06-30T08:00:00.000Z', intervalDays: 1 },
    ]);

    expect(getNoteReviewHistorySummary(entries, new Date('2026-07-11T12:00:00.000Z'))).toEqual({
      totalCompletions: 4,
      activeDays: 3,
      currentStreak: 2,
    });
    expect(getNoteReviewHistorySummary(entries, new Date('2026-07-12T12:00:00.000Z')).currentStreak).toBe(2);
  });
});
