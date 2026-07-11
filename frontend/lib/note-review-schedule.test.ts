import { describe, expect, it } from 'vitest';
import {
  clearNoteReviewSchedule,
  createNoteReviewSchedule,
  getNoteReviewScheduleKey,
  getNoteReviewScheduleStatus,
  normalizeNoteReviewSchedule,
  readNoteReviewSchedule,
  writeNoteReviewSchedule,
} from './note-review-schedule';

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

  it('labels overdue, today, tomorrow, and upcoming schedules', () => {
    const schedule = createNoteReviewSchedule(3, now)!;
    expect(getNoteReviewScheduleStatus(schedule, new Date('2026-07-15T01:00:00.000Z')).label).toBe('1일 지남');
    expect(getNoteReviewScheduleStatus(schedule, new Date('2026-07-14T01:00:00.000Z'))).toMatchObject({ state: 'due', label: '오늘 복습' });
    expect(getNoteReviewScheduleStatus(schedule, new Date('2026-07-13T01:00:00.000Z'))).toMatchObject({ state: 'upcoming', label: '내일 복습' });
    expect(getNoteReviewScheduleStatus(schedule, new Date('2026-07-12T01:00:00.000Z')).label).toBe('2일 후 복습');
  });
});
