export interface NoteReviewHistoryEntry {
  id: string;
  noteId: string;
  noteTitle: string;
  completedAt: string;
  intervalDays: number;
}

export interface NoteReviewHistorySummary {
  totalCompletions: number;
  activeDays: number;
  currentStreak: number;
}

export interface RecordNoteReviewInput {
  noteId: string;
  noteTitle: string;
  intervalDays: number;
}

type ReviewHistoryStorage = Pick<Storage, 'getItem' | 'setItem'>;

const MAX_HISTORY_ENTRIES = 200;
export const NOTE_REVIEW_HISTORY_STORAGE_KEY = 'ie_note_review_history';

function resolveStorage(storage?: ReviewHistoryStorage): ReviewHistoryStorage | null {
  if (storage) return storage;
  if (typeof window === 'undefined') return null;
  return window.localStorage;
}

function localDateKey(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function normalizeEntry(value: unknown): NoteReviewHistoryEntry | null {
  if (!value || typeof value !== 'object') return null;
  const record = value as Partial<NoteReviewHistoryEntry>;
  const noteId = typeof record.noteId === 'string' ? record.noteId.trim() : '';
  const noteTitle = typeof record.noteTitle === 'string' ? record.noteTitle.trim() : '';
  const completedAt = typeof record.completedAt === 'string' ? record.completedAt : '';
  const intervalDays = Number.isInteger(record.intervalDays) ? Number(record.intervalDays) : 0;
  if (!noteId || Number.isNaN(Date.parse(completedAt)) || intervalDays < 1 || intervalDays > 365) {
    return null;
  }
  const completedDate = new Date(completedAt);
  return {
    id: `${noteId}:${localDateKey(completedDate)}`,
    noteId,
    noteTitle: noteTitle || '제목 없음',
    completedAt,
    intervalDays,
  };
}

export function normalizeNoteReviewHistory(value: unknown): NoteReviewHistoryEntry[] {
  if (!Array.isArray(value)) return [];
  const byId = new Map<string, NoteReviewHistoryEntry>();
  for (const raw of value) {
    const entry = normalizeEntry(raw);
    if (!entry) continue;
    const current = byId.get(entry.id);
    if (!current || Date.parse(entry.completedAt) >= Date.parse(current.completedAt)) {
      byId.set(entry.id, entry);
    }
  }
  return Array.from(byId.values())
    .sort((a, b) => Date.parse(b.completedAt) - Date.parse(a.completedAt))
    .slice(0, MAX_HISTORY_ENTRIES);
}

export function readNoteReviewHistory(storage?: ReviewHistoryStorage): NoteReviewHistoryEntry[] {
  const target = resolveStorage(storage);
  if (!target) return [];
  try {
    const raw = target.getItem(NOTE_REVIEW_HISTORY_STORAGE_KEY);
    return normalizeNoteReviewHistory(raw ? JSON.parse(raw) : null);
  } catch {
    return [];
  }
}

export function recordNoteReviewCompletion(
  input: RecordNoteReviewInput,
  storage?: ReviewHistoryStorage,
  now = new Date()
): NoteReviewHistoryEntry[] {
  const target = resolveStorage(storage);
  if (Number.isNaN(now.getTime())) return target ? readNoteReviewHistory(target) : [];
  const nextEntry = normalizeEntry({
    ...input,
    completedAt: now.toISOString(),
  });
  if (!nextEntry) return target ? readNoteReviewHistory(target) : [];

  const next = normalizeNoteReviewHistory([
    ...(target ? readNoteReviewHistory(target) : []),
    nextEntry,
  ]);
  target?.setItem(NOTE_REVIEW_HISTORY_STORAGE_KEY, JSON.stringify(next));
  return next;
}

function startOfLocalDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function addLocalDays(value: Date, days: number): Date {
  const result = startOfLocalDay(value);
  result.setDate(result.getDate() + days);
  return result;
}

export interface NoteReviewActivityDay {
  dateKey: string;
  label: string;
  count: number;
  isToday: boolean;
}

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토'] as const;

export function getNoteReviewActivityDays(
  entries: NoteReviewHistoryEntry[],
  now = new Date(),
  windowDays = 7
): NoteReviewActivityDay[] {
  if (Number.isNaN(now.getTime())) return [];
  const days = Number.isFinite(windowDays) ? Math.max(1, Math.floor(windowDays)) : 7;
  const today = startOfLocalDay(now);
  const counts = new Map<string, number>();
  for (const entry of normalizeNoteReviewHistory(entries)) {
    const key = localDateKey(new Date(entry.completedAt));
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  return Array.from({ length: days }, (_, index) => {
    const date = addLocalDays(today, index - days + 1);
    const dateKey = localDateKey(date);
    return {
      dateKey,
      label: WEEKDAY_LABELS[date.getDay()],
      count: counts.get(dateKey) ?? 0,
      isToday: index === days - 1,
    };
  });
}

export function getNoteReviewHistorySummary(
  entries: NoteReviewHistoryEntry[],
  now = new Date(),
  windowDays = 7
): NoteReviewHistorySummary {
  const days = Number.isFinite(windowDays) ? Math.max(1, Math.floor(windowDays)) : 7;
  if (Number.isNaN(now.getTime())) {
    return { totalCompletions: 0, activeDays: 0, currentStreak: 0 };
  }
  const normalized = normalizeNoteReviewHistory(entries);
  const today = startOfLocalDay(now);
  const cutoff = addLocalDays(today, -(days - 1)).getTime();
  const recent = normalized.filter((entry) => {
    const day = startOfLocalDay(new Date(entry.completedAt)).getTime();
    return day >= cutoff && day <= today.getTime();
  });
  const activeDateKeys = new Set(recent.map((entry) => localDateKey(new Date(entry.completedAt))));
  const allDateKeys = new Set(normalized.map((entry) => localDateKey(new Date(entry.completedAt))));

  let cursor = today;
  if (!allDateKeys.has(localDateKey(cursor))) {
    cursor = addLocalDays(today, -1);
  }
  let currentStreak = 0;
  while (allDateKeys.has(localDateKey(cursor))) {
    currentStreak += 1;
    cursor = addLocalDays(cursor, -1);
  }

  return {
    totalCompletions: recent.length,
    activeDays: activeDateKeys.size,
    currentStreak,
  };
}
