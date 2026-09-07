import { describe, expect, it } from 'vitest';
import {
  NOTE_REVIEW_HISTORY_STORAGE_KEY,
  buildNoteReviewHistoryMarkdown,
  getNoteReviewActivityDays,
  getNoteReviewHistorySummary,
  getLatestNoteReviewIntervalDays,
  getNoteReviewSelectionState,
  normalizeNoteReviewHistory,
  readNoteReviewHistory,
  recordNoteReviewCompletion,
} from './note-review-history';
import { getNextReviewInterval } from './note-review-schedule';
import { setAuthSession, type AuthSession } from './auth-session';

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

function createMemoryStorage() {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => data.set(key, value),
  };
}

describe('note-review-history', () => {
  it('finds the latest valid interval for one note across legacy entries', () => {
    expect(getLatestNoteReviewIntervalDays([
      { noteId: 'note-1', completedAt: '2026-07-09T08:00:00.000Z', intervalDays: 2 },
      { noteId: 'note-2', completedAt: '2026-07-11T09:00:00.000Z', intervalDays: 365 },
      { noteId: 'note-1', completedAt: '2026-07-11T08:00:00.000Z', intervalDays: 6 },
      { noteId: 'note-1', completedAt: '2026-07-12T08:00:00.000Z', intervalDays: 0 },
    ], 'note-1')).toBe(6);
    expect(getLatestNoteReviewIntervalDays([], 'note-1')).toBeNull();
  });
  it('keeps the original basis stable when a future schedule is reloaded and reselected', () => {
    const schedule = {
      dueAt: '2026-07-15T08:00:00.000Z',
      intervalDays: 6,
      scheduledAt: '2026-07-11T07:59:00.000Z',
    };
    const entries = [{
      noteId: 'note-1',
      completedAt: '2026-07-11T08:00:00.000Z',
      intervalDays: 6,
      grade: 'hard',
      baseIntervalDays: 4,
    }];

    const reloaded = getNoteReviewSelectionState(
      entries,
      'note-1',
      schedule,
      new Date('2026-07-12T08:00:00.000Z')
    );
    expect(reloaded).toEqual({ previousIntervalDays: 4, selectedGrade: 'hard' });
    expect(getNextReviewInterval('easy', reloaded.previousIntervalDays ?? undefined)).toBe(12);

    const firstReview = getNoteReviewSelectionState([{
      noteId: 'note-1',
      completedAt: '2026-07-11T08:00:00.000Z',
      intervalDays: 7,
      grade: 'easy',
      baseIntervalDays: null,
    }], 'note-1', {
      ...schedule,
      intervalDays: 7,
    }, new Date('2026-07-12T08:00:00.000Z'));
    expect(firstReview).toEqual({ previousIntervalDays: null, selectedGrade: 'easy' });
    expect(getNextReviewInterval('good', firstReview.previousIntervalDays ?? undefined)).toBe(3);
    expect(getNoteReviewSelectionState(
      entries,
      'note-1',
      schedule,
      new Date('2026-07-15T08:00:00.000Z')
    )).toEqual({ previousIntervalDays: 6, selectedGrade: null });
  });

  it('reads legacy entries without adaptive review metadata', () => {
    const schedule = {
      dueAt: '2026-07-15T08:00:00.000Z',
      intervalDays: 3,
      scheduledAt: '2026-07-11T07:59:00.000Z',
    };
    expect(getNoteReviewSelectionState([
      { noteId: 'note-1', completedAt: '2026-07-11T08:00:00.000Z', intervalDays: 3 },
    ], 'note-1', schedule, new Date('2026-07-12T08:00:00.000Z'))).toEqual({
      previousIntervalDays: 3,
      selectedGrade: null,
    });
  });

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

  it('preserves valid schedule binding metadata and drops malformed values', () => {
    const history = normalizeNoteReviewHistory([
      { noteId: 'valid', completedAt: '2026-07-11T08:00:00.000Z', intervalDays: 3, scheduleScheduledAt: '2026-07-11T07:59:00.000Z' },
      { noteId: 'invalid', completedAt: '2026-07-12T08:00:00.000Z', intervalDays: 3, scheduleScheduledAt: '2026-07-12 07:59:00' },
    ]);

    expect(history.find((entry) => entry.noteId === 'valid')?.scheduleScheduledAt)
      .toBe('2026-07-11T07:59:00.000Z');
    expect(history.find((entry) => entry.noteId === 'invalid'))
      .not.toHaveProperty('scheduleScheduledAt');
  });

  it('records one completion per note and local day', () => {
    const storage = createMemoryStorage();
    recordNoteReviewCompletion(
      { noteId: 'note-1', noteTitle: '첫 노트', intervalDays: 1 },
      storage,
      new Date('2026-07-11T01:00:00.000Z')
    );
    const updated = recordNoteReviewCompletion(
      {
        noteId: 'note-1',
        noteTitle: '첫 노트',
        intervalDays: 7,
        grade: 'easy',
        baseIntervalDays: null,
        scheduleScheduledAt: '2026-07-11T07:59:00.000Z',
      },
      storage,
      new Date('2026-07-11T08:00:00.000Z')
    );

    expect(updated).toHaveLength(1);
    expect(updated[0]).toMatchObject({
      intervalDays: 7,
      grade: 'easy',
      baseIntervalDays: null,
      scheduleScheduledAt: '2026-07-11T07:59:00.000Z',
    });
    expect(storage.getItem(NOTE_REVIEW_HISTORY_STORAGE_KEY)).toContain('note-1');
    expect(readNoteReviewHistory(storage)).toEqual(updated);
  });

  it('서로 다른 계정의 복습 이력을 같은 Storage 안에서 격리한다', () => {
    const storage = createMemoryStorage();
    try {
      setAuthSession(authSession('account-a'));
      recordNoteReviewCompletion(
        { noteId: 'note-a', noteTitle: 'A 노트', intervalDays: 1 },
        storage,
        new Date('2026-07-11T01:00:00.000Z'),
      );

      setAuthSession(authSession('account-b'));
      expect(readNoteReviewHistory(storage)).toEqual([]);
      recordNoteReviewCompletion(
        { noteId: 'note-b', noteTitle: 'B 노트', intervalDays: 3 },
        storage,
        new Date('2026-07-12T01:00:00.000Z'),
      );

      setAuthSession(authSession('account-a'));
      expect(readNoteReviewHistory(storage).map(({ noteId }) => noteId)).toEqual(['note-a']);
    } finally {
      setAuthSession(null);
    }
  });

  it('builds an oldest-to-today seven-day activity series', () => {
    const entries = normalizeNoteReviewHistory([
      { noteId: 'a', noteTitle: 'A', completedAt: '2026-07-10T08:00:00.000Z', intervalDays: 1 },
      { noteId: 'b', noteTitle: 'B', completedAt: '2026-07-10T09:00:00.000Z', intervalDays: 3 },
      { noteId: 'c', noteTitle: 'C', completedAt: '2026-07-08T08:00:00.000Z', intervalDays: 7 },
    ]);

    const activity = getNoteReviewActivityDays(entries, new Date('2026-07-11T12:00:00.000Z'), 4);
    expect(activity.map(({ dateKey, count, isToday }) => ({ dateKey, count, isToday }))).toEqual([
      { dateKey: '2026-07-08', count: 1, isToday: false },
      { dateKey: '2026-07-09', count: 0, isToday: false },
      { dateKey: '2026-07-10', count: 2, isToday: false },
      { dateKey: '2026-07-11', count: 0, isToday: true },
    ]);
    expect(getNoteReviewActivityDays(entries, new Date('invalid'))).toEqual([]);
  });

  it('builds a weekly review history markdown report', () => {
    const entries = normalizeNoteReviewHistory([
      { noteId: 'note 1', noteTitle: '  [RAG]\n노트  ', completedAt: '2026-07-11T08:00:00.000Z', intervalDays: 3 },
      { noteId: 'note-2', noteTitle: '둘째 노트', completedAt: '2026-07-10T08:00:00.000Z', intervalDays: 7 },
    ]);
    const markdown = buildNoteReviewHistoryMarkdown(entries, {
      title: '  나의\n복습  ',
      now: new Date('2026-07-11T12:00:00.000Z'),
    });

    expect(markdown).toContain('# 나의 복습');
    expect(markdown).toContain('- 연속 학습: 2일');
    expect(markdown).toContain('- 최근 7일 완료: 2회');
    expect(markdown).toContain('2026-07-11 (토): 1회');
    expect(markdown).toContain('[\\[RAG\\] 노트](/notes/note%201#study-progress)');
    expect(buildNoteReviewHistoryMarkdown([], { now: new Date('2026-07-11T12:00:00.000Z') }))
      .toContain('복습 기록이 없습니다.');
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
