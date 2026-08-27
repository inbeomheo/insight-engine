import { describe, expect, it } from 'vitest';
import {
  NOTE_REVIEW_GRADE_OPTIONS,
  clearNoteReviewSchedule,
  createNoteReviewSchedule,
  getNextReviewInterval,
  getPreviousIntervalForNewReviewSession,
  getNoteReviewScheduleKey,
  getNoteReviewScheduleStatus,
  normalizeNoteReviewSchedule,
  readNoteReviewSchedule,
  writeNoteReviewSchedule,
} from './note-review-schedule';
import { setAuthSession, type AuthSession } from './auth-session';

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

function createMemoryStorage() {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => data.set(key, value),
    removeItem: (key: string) => data.delete(key),
  };
}

describe('note-review-schedule', () => {
  const now = new Date('2026-07-11T10:00:00.000Z');

  it('exposes Korean labels for every recall grade', () => {
    expect(NOTE_REVIEW_GRADE_OPTIONS).toEqual([
      { value: 'again', label: '다시' },
      { value: 'hard', label: '어려움' },
      { value: 'good', label: '보통' },
      { value: 'easy', label: '쉬움' },
    ]);
  });

  it('calculates the first review interval from recall grade', () => {
    expect(getNextReviewInterval('again')).toBe(1);
    expect(getNextReviewInterval('hard')).toBe(2);
    expect(getNextReviewInterval('good')).toBe(3);
    expect(getNextReviewInterval('easy')).toBe(7);
  });

  it('adjusts a valid previous interval and clamps the result', () => {
    expect(getNextReviewInterval('again', 10)).toBe(1);
    expect(getNextReviewInterval('hard', 3)).toBe(5);
    expect(getNextReviewInterval('good', 10)).toBe(20);
    expect(getNextReviewInterval('easy', 200)).toBe(365);
  });

  it('promotes the active interval only when starting a new review session', () => {
    const activeSchedule = createNoteReviewSchedule(6, now);
    const promoted = getPreviousIntervalForNewReviewSession(activeSchedule, 3);

    expect(promoted).toBe(6);
    expect(getNextReviewInterval('good', promoted ?? undefined)).toBe(12);
    expect(getPreviousIntervalForNewReviewSession(null, 3)).toBe(3);
  });

  it('uses first-review intervals for missing or invalid previous values', () => {
    expect(getNextReviewInterval('good', 0)).toBe(3);
    expect(getNextReviewInterval('easy', 1.5)).toBe(7);
    expect(getNextReviewInterval('hard', Number.NaN)).toBe(2);
    expect(getNextReviewInterval('again', 366)).toBe(1);
  });

  it('creates a deterministic review schedule', () => {
    expect(createNoteReviewSchedule(3, now)).toEqual({
      dueAt: '2026-07-14T10:00:00.000Z',
      intervalDays: 3,
      scheduledAt: '2026-07-11T10:00:00.000Z',
    });
    expect(createNoteReviewSchedule(0, now)).toBeNull();
    expect(createNoteReviewSchedule(366, now)).toBeNull();
  });

  it('normalizes invalid stored values', () => {
    expect(normalizeNoteReviewSchedule(null)).toBeNull();
    expect(normalizeNoteReviewSchedule({ dueAt: 'bad', intervalDays: 3, scheduledAt: now.toISOString() })).toBeNull();
    expect(normalizeNoteReviewSchedule({
      dueAt: '2026-07-14T10:00:00.000Z',
      intervalDays: 3,
      scheduledAt: '2026-07-11T10:00:00.000Z',
    })).not.toBeNull();
  });

  it('persists and clears a schedule', () => {
    const storage = createMemoryStorage();
    const schedule = writeNoteReviewSchedule('note-1', 7, storage, now);
    expect(storage.getItem(getNoteReviewScheduleKey('note-1'))).toContain('2026-07-18');
    expect(readNoteReviewSchedule('note-1', storage)).toEqual(schedule);
    clearNoteReviewSchedule('note-1', storage);
    expect(readNoteReviewSchedule('note-1', storage)).toBeNull();
  });

  it('계정별로 같은 노트의 복습 일정을 따로 보존한다', () => {
    const storage = createMemoryStorage();
    try {
      setAuthSession(authSession('account-a'));
      writeNoteReviewSchedule('shared-note', 2, storage, now);

      setAuthSession(authSession('account-b'));
      expect(readNoteReviewSchedule('shared-note', storage)).toBeNull();
      writeNoteReviewSchedule('shared-note', 7, storage, now);

      setAuthSession(authSession('account-a'));
      expect(readNoteReviewSchedule('shared-note', storage)?.intervalDays).toBe(2);
    } finally {
      setAuthSession(null);
    }
  });

  it('labels overdue, today, tomorrow, and upcoming schedules', () => {
    const schedule = createNoteReviewSchedule(3, now)!;
    expect(getNoteReviewScheduleStatus(schedule, new Date('2026-07-15T01:00:00.000Z')).label).toBe('1일 지남');
    expect(getNoteReviewScheduleStatus(schedule, new Date('2026-07-14T01:00:00.000Z'))).toMatchObject({ state: 'due', label: '오늘 복습' });
    expect(getNoteReviewScheduleStatus(schedule, new Date('2026-07-13T01:00:00.000Z'))).toMatchObject({ state: 'upcoming', label: '내일 복습' });
    expect(getNoteReviewScheduleStatus(schedule, new Date('2026-07-12T01:00:00.000Z')).label).toBe('2일 후 복습');
  });
});
