import { getAccountStorageKey } from './storage';

export interface NoteReviewSchedule {
  dueAt: string;
  intervalDays: number;
  scheduledAt: string;
}

export type NoteReviewScheduleState = 'due' | 'upcoming' | 'invalid';

export interface NoteReviewScheduleStatus {
  state: NoteReviewScheduleState;
  label: string;
  daysUntilDue: number;
}

type ReviewScheduleStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

const DAY_MS = 24 * 60 * 60 * 1000;

export type NoteReviewGrade = 'again' | 'hard' | 'good' | 'easy';

export interface NoteReviewGradeOption {
  value: NoteReviewGrade;
  label: string;
}

export const NOTE_REVIEW_GRADE_OPTIONS: readonly NoteReviewGradeOption[] = [
  { value: 'again', label: '다시' },
  { value: 'hard', label: '어려움' },
  { value: 'good', label: '보통' },
  { value: 'easy', label: '쉬움' },
];

const FIRST_REVIEW_INTERVALS: Record<NoteReviewGrade, number> = {
  again: 1,
  hard: 2,
  good: 3,
  easy: 7,
};

const REVIEW_INTERVAL_MULTIPLIERS: Record<NoteReviewGrade, number> = {
  again: 0,
  hard: 1.5,
  good: 2,
  easy: 3,
};

export function getNextReviewInterval(
  grade: NoteReviewGrade,
  previousIntervalDays?: number
): number {
  const hasValidPrevious = Number.isInteger(previousIntervalDays)
    && Number(previousIntervalDays) >= 1
    && Number(previousIntervalDays) <= 365;
  if (!hasValidPrevious) return FIRST_REVIEW_INTERVALS[grade];

  const nextInterval = grade === 'again'
    ? 1
    : Number(previousIntervalDays) * REVIEW_INTERVAL_MULTIPLIERS[grade];
  return Math.min(365, Math.max(1, Math.round(nextInterval)));
}

export function getNoteReviewScheduleKey(noteId: string, namespace?: string): string {
  return getAccountStorageKey(`ie_note_review_schedule:${noteId}`, namespace);
}

function resolveStorage(storage?: ReviewScheduleStorage): ReviewScheduleStorage | null {
  if (storage) return storage;
  if (typeof window === 'undefined') return null;
  return window.localStorage;
}

function normalizeIntervalDays(value: unknown): number | null {
  return Number.isInteger(value) && Number(value) > 0 && Number(value) <= 365
    ? Number(value)
    : null;
}

export function getPreviousIntervalForNewReviewSession(
  activeSchedule: NoteReviewSchedule | null,
  currentPreviousIntervalDays: number | null
): number | null {
  return normalizeIntervalDays(activeSchedule?.intervalDays)
    ?? normalizeIntervalDays(currentPreviousIntervalDays);
}

export function normalizeNoteReviewSchedule(value: unknown): NoteReviewSchedule | null {
  if (!value || typeof value !== 'object') return null;
  const record = value as Partial<NoteReviewSchedule>;
  const intervalDays = normalizeIntervalDays(record.intervalDays);
  const dueAt = typeof record.dueAt === 'string' ? record.dueAt : '';
  const scheduledAt = typeof record.scheduledAt === 'string' ? record.scheduledAt : '';
  if (!intervalDays || Number.isNaN(Date.parse(dueAt)) || Number.isNaN(Date.parse(scheduledAt))) {
    return null;
  }
  return { dueAt, intervalDays, scheduledAt };
}

export function createNoteReviewSchedule(
  intervalDays: number,
  now = new Date()
): NoteReviewSchedule | null {
  const normalizedInterval = normalizeIntervalDays(intervalDays);
  if (!normalizedInterval || Number.isNaN(now.getTime())) return null;
  return {
    dueAt: new Date(now.getTime() + normalizedInterval * DAY_MS).toISOString(),
    intervalDays: normalizedInterval,
    scheduledAt: now.toISOString(),
  };
}

export function readNoteReviewSchedule(
  noteId: string,
  storage?: ReviewScheduleStorage
): NoteReviewSchedule | null {
  const target = resolveStorage(storage);
  if (!target) return null;
  try {
    const raw = target.getItem(getNoteReviewScheduleKey(noteId));
    return normalizeNoteReviewSchedule(raw ? JSON.parse(raw) : null);
  } catch {
    return null;
  }
}

export function writeNoteReviewSchedule(
  noteId: string,
  intervalDays: number,
  storage?: ReviewScheduleStorage,
  now = new Date()
): NoteReviewSchedule | null {
  const schedule = createNoteReviewSchedule(intervalDays, now);
  const target = resolveStorage(storage);
  if (!schedule || !target) return schedule;
  target.setItem(getNoteReviewScheduleKey(noteId), JSON.stringify(schedule));
  return schedule;
}

export function clearNoteReviewSchedule(noteId: string, storage?: ReviewScheduleStorage): void {
  resolveStorage(storage)?.removeItem(getNoteReviewScheduleKey(noteId));
}

function startOfLocalDay(value: Date): number {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
}

export function getNoteReviewScheduleStatus(
  schedule: NoteReviewSchedule,
  now = new Date()
): NoteReviewScheduleStatus {
  const due = new Date(schedule.dueAt);
  if (Number.isNaN(due.getTime()) || Number.isNaN(now.getTime())) {
    return { state: 'invalid', label: '일정 확인 필요', daysUntilDue: 0 };
  }

  const daysUntilDue = Math.round((startOfLocalDay(due) - startOfLocalDay(now)) / DAY_MS);
  if (daysUntilDue < 0) {
    return { state: 'due', label: `${Math.abs(daysUntilDue)}일 지남`, daysUntilDue };
  }
  if (daysUntilDue === 0) {
    return { state: 'due', label: '오늘 복습', daysUntilDue: 0 };
  }
  if (daysUntilDue === 1) {
    return { state: 'upcoming', label: '내일 복습', daysUntilDue };
  }
  return { state: 'upcoming', label: `${daysUntilDue}일 후 복습`, daysUntilDue };
}
