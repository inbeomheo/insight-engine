export type NoteStudyKind = 'learning' | 'review';

export interface NoteStudyCounts {
  learning: number;
  review: number;
}

export interface NoteStudyProgress {
  learning: number[];
  review: number[];
  updatedAt: string | null;
}

export interface NoteStudySummary {
  completed: number;
  total: number;
  percent: number;
  completedLearning: number;
  completedReview: number;
}

export interface NoteStudyMarkdownInput {
  title: string;
  sourceUrl?: string;
  learningPoints?: string[];
  reviewQuestions?: Array<{ question: string; answer?: string }>;
  progress: NoteStudyProgress;
}

type NoteStudyStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export function getNoteStudyProgressKey(noteId: string): string {
  return `ie_note_study_progress:${noteId}`;
}

function sanitizeIndexes(value: unknown, max: number): number[] {
  if (!Array.isArray(value)) return [];
  return Array.from(
    new Set(
      value.filter((item): item is number =>
        Number.isInteger(item) && item >= 0 && item < max
      )
    )
  ).sort((a, b) => a - b);
}

export function normalizeNoteStudyProgress(
  value: unknown,
  counts: NoteStudyCounts
): NoteStudyProgress {
  const record = value && typeof value === 'object' ? value as Partial<NoteStudyProgress> : {};
  return {
    learning: sanitizeIndexes(record.learning, counts.learning),
    review: sanitizeIndexes(record.review, counts.review),
    updatedAt: typeof record.updatedAt === 'string' ? record.updatedAt : null,
  };
}

export function getNoteStudySummary(
  progress: NoteStudyProgress,
  counts: NoteStudyCounts
): NoteStudySummary {
  const normalized = normalizeNoteStudyProgress(progress, counts);
  const total = Math.max(0, counts.learning) + Math.max(0, counts.review);
  const completedLearning = normalized.learning.length;
  const completedReview = normalized.review.length;
  const completed = completedLearning + completedReview;
  return {
    completed,
    total,
    percent: total > 0 ? Math.round((completed / total) * 100) : 0,
    completedLearning,
    completedReview,
  };
}

export function getVisibleNoteStudyIndexes(
  total: number,
  completedIndexes: number[],
  showCompleted: boolean
): number[] {
  const count = Math.max(0, total);
  const completed = new Set(sanitizeIndexes(completedIndexes, count));
  return Array.from({ length: count }, (_, index) => index).filter(
    (index) => showCompleted || !completed.has(index)
  );
}

export function toggleNoteStudyItem(
  progress: NoteStudyProgress,
  kind: NoteStudyKind,
  index: number,
  counts: NoteStudyCounts,
  updatedAt = new Date().toISOString()
): NoteStudyProgress {
  const normalized = normalizeNoteStudyProgress(progress, counts);
  const max = kind === 'learning' ? counts.learning : counts.review;
  if (!Number.isInteger(index) || index < 0 || index >= max) {
    return normalized;
  }

  const current = new Set(normalized[kind]);
  if (current.has(index)) {
    current.delete(index);
  } else {
    current.add(index);
  }

  return {
    ...normalized,
    [kind]: Array.from(current).sort((a, b) => a - b),
    updatedAt,
  };
}

function resolveStorage(storage?: NoteStudyStorage): NoteStudyStorage | null {
  if (storage) return storage;
  if (typeof window === 'undefined') return null;
  return window.localStorage;
}

export function readNoteStudyProgress(
  noteId: string,
  counts: NoteStudyCounts,
  storage?: NoteStudyStorage
): NoteStudyProgress {
  const target = resolveStorage(storage);
  if (!target) return normalizeNoteStudyProgress(null, counts);
  try {
    const raw = target.getItem(getNoteStudyProgressKey(noteId));
    return normalizeNoteStudyProgress(raw ? JSON.parse(raw) : null, counts);
  } catch {
    return normalizeNoteStudyProgress(null, counts);
  }
}

export function writeNoteStudyProgress(
  noteId: string,
  progress: NoteStudyProgress,
  counts: NoteStudyCounts,
  storage?: NoteStudyStorage
): NoteStudyProgress {
  const normalized = normalizeNoteStudyProgress(progress, counts);
  const target = resolveStorage(storage);
  if (target) {
    target.setItem(getNoteStudyProgressKey(noteId), JSON.stringify(normalized));
  }
  return normalized;
}

export function clearNoteStudyProgress(noteId: string, storage?: NoteStudyStorage): void {
  const target = resolveStorage(storage);
  target?.removeItem(getNoteStudyProgressKey(noteId));
}

function checkbox(done: boolean): string {
  return done ? '[x]' : '[ ]';
}

export function buildNoteStudyMarkdown(input: NoteStudyMarkdownInput): string {
  const learningPoints = input.learningPoints ?? [];
  const reviewQuestions = input.reviewQuestions ?? [];
  const counts = { learning: learningPoints.length, review: reviewQuestions.length };
  const progress = normalizeNoteStudyProgress(input.progress, counts);
  const summary = getNoteStudySummary(progress, counts);
  const lines = [
    `# ${input.title || '제목 없음'} 복습 노트`,
    '',
    `- 진행률: ${summary.completed}/${summary.total} (${summary.percent}%)`,
  ];

  if (input.sourceUrl) {
    lines.push(`- 원본: ${input.sourceUrl}`);
  }
  if (progress.updatedAt) {
    lines.push(`- 마지막 체크: ${progress.updatedAt}`);
  }

  if (learningPoints.length > 0) {
    lines.push('', '## 학습 포인트');
    learningPoints.forEach((point, index) => {
      lines.push(`- ${checkbox(progress.learning.includes(index))} ${point}`);
    });
  }

  if (reviewQuestions.length > 0) {
    lines.push('', '## 복습 질문');
    reviewQuestions.forEach((item, index) => {
      lines.push(`- ${checkbox(progress.review.includes(index))} ${item.question}`);
      if (item.answer?.trim()) {
        lines.push(`  - 답: ${item.answer}`);
      }
    });
  }

  return `${lines.join('\n')}\n`;
}
