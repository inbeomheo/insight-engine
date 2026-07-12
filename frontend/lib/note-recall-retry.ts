export interface NoteRecallRetryState {
  completedIndexes: number[];
}

export interface NoteRecallRetrySummary {
  completed: number;
  total: number;
  isComplete: boolean;
}

function normalizeTotal(total: number): number {
  return Number.isFinite(total) ? Math.max(0, Math.floor(total)) : 0;
}

export function normalizeNoteRecallRetryState(value: unknown, total: number): NoteRecallRetryState {
  const count = normalizeTotal(total);
  const record = value && typeof value === 'object' ? value as Partial<NoteRecallRetryState> : {};
  const indexes = Array.isArray(record.completedIndexes) ? record.completedIndexes : [];
  return {
    completedIndexes: Array.from(new Set(indexes.filter((index): index is number =>
      Number.isInteger(index) && index >= 0 && index < count
    ))).sort((a, b) => a - b),
  };
}

export function createNoteRecallRetryState(total: number): NoteRecallRetryState {
  return normalizeNoteRecallRetryState(null, total);
}

export function toggleNoteRecallRetryItem(state: NoteRecallRetryState, index: number, total: number): NoteRecallRetryState {
  const normalized = normalizeNoteRecallRetryState(state, total);
  const count = normalizeTotal(total);
  if (!Number.isInteger(index) || index < 0 || index >= count) return normalized;
  const completed = new Set(normalized.completedIndexes);
  if (completed.has(index)) completed.delete(index);
  else completed.add(index);
  return { completedIndexes: Array.from(completed).sort((a, b) => a - b) };
}

export function getNoteRecallRetrySummary(state: NoteRecallRetryState, total: number): NoteRecallRetrySummary {
  const count = normalizeTotal(total);
  const completed = normalizeNoteRecallRetryState(state, count).completedIndexes.length;
  return { completed, total: count, isComplete: count > 0 && completed === count };
}
