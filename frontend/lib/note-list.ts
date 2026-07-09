import type { NoteListItem } from './api';
import {
  getNoteStudySummary,
  type NoteStudyCounts,
  type NoteStudyProgress,
  type NoteStudySummary,
} from './note-study-progress';

export type NoteFacet =
  | { type: 'concept'; value: string }
  | { type: 'tag'; value: string }
  | { type: 'source'; value: string };

export function getNoteSourceLabel(type?: string): string {
  if (type === 'youtube') return 'YouTube';
  if (type === 'text') return '직접 텍스트';
  if (type === 'article') return 'Article';
  if (type === 'document') return '문서';
  if (type === 'voice') return '음성';
  return '기타';
}

function normalize(value: string): string {
  return value.trim().toLowerCase();
}

function preferDisplayLabel(current: string, next: string): string {
  if (current === current.toLowerCase() && next !== next.toLowerCase()) return next;
  return current;
}

export function noteMatchesFacet(note: NoteListItem, facet: NoteFacet): boolean {
  const target = normalize(facet.value);
  if (!target) return true;

  if (facet.type === 'concept') {
    return (note.key_concepts ?? []).some((concept) => normalize(concept) === target);
  }
  if (facet.type === 'tag') {
    return (note.tags ?? []).some((tag) => normalize(tag) === target);
  }

  return normalize(getNoteSourceLabel(note.source?.type)) === target;
}

export function filterNotesByFacet(notes: NoteListItem[], facet: NoteFacet | null): NoteListItem[] {
  if (!facet) return notes;
  return notes.filter((note) => noteMatchesFacet(note, facet));
}

export function buildNoteFacetHref(facet: NoteFacet): string {
  const params = new URLSearchParams();
  params.set(facet.type, facet.value);
  return `/notes?${params.toString()}`;
}

export function parseNoteFacetSearchParams(
  params: Pick<URLSearchParams, 'get'> | null | undefined
): NoteFacet | null {
  if (!params) return null;
  const concept = params.get('concept')?.trim();
  if (concept) return { type: 'concept', value: concept };
  const tag = params.get('tag')?.trim();
  if (tag) return { type: 'tag', value: tag };
  const source = params.get('source')?.trim();
  if (source) return { type: 'source', value: source };
  return null;
}

export function sortNotesByRecent(notes: NoteListItem[]): NoteListItem[] {
  return [...notes].sort((a, b) => {
    const timeA = Date.parse(a.created_at);
    const timeB = Date.parse(b.created_at);
    return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA);
  });
}

export interface NoteConceptCluster {
  concept: string;
  count: number;
  notes: NoteListItem[];
}

export function getNoteConceptClusters(
  notes: NoteListItem[],
  options: { limit?: number; notesPerCluster?: number; minNotes?: number } = {}
): NoteConceptCluster[] {
  const limit = options.limit ?? 4;
  const notesPerCluster = options.notesPerCluster ?? 3;
  const minNotes = options.minNotes ?? 2;
  const clusters = new Map<string, { concept: string; notes: NoteListItem[] }>();

  for (const note of notes) {
    const seenInNote = new Set<string>();
    for (const rawConcept of note.key_concepts ?? []) {
      const concept = rawConcept.trim();
      const key = normalize(concept);
      if (!concept || seenInNote.has(key)) continue;
      seenInNote.add(key);
      const current = clusters.get(key) ?? { concept, notes: [] };
      current.concept = preferDisplayLabel(current.concept, concept);
      current.notes.push(note);
      clusters.set(key, current);
    }
  }

  return Array.from(clusters.values())
    .map((cluster) => ({
      concept: cluster.concept,
      count: cluster.notes.length,
      notes: sortNotesByRecent(cluster.notes).slice(0, notesPerCluster),
    }))
    .filter((cluster) => cluster.count >= minNotes)
    .sort((a, b) => {
      if (a.count !== b.count) return b.count - a.count;
      return a.concept.localeCompare(b.concept);
    })
    .slice(0, limit);
}

export function getFacetLabel(facet: NoteFacet): string {
  if (facet.type === 'concept') return `개념: ${facet.value}`;
  if (facet.type === 'tag') return `태그: ${facet.value}`;
  return `출처: ${facet.value}`;
}

export interface NoteStudyResumeItem {
  note: NoteListItem;
  summary: NoteStudySummary;
  updatedAt: string | null;
}

export type NoteStudyStatus = 'not-started' | 'in-progress' | 'completed';
export type NoteStudyCardKind = 'review-needed' | 'study-start' | 'completed' | 'recent';
export type NoteStudyPlanKind = 'continue' | 'start';
export interface NoteStudyPlanItem extends NoteStudyResumeItem {
  kind: NoteStudyPlanKind;
  label: string;
  actionLabel: string;
  remaining: number;
}
export const NOTE_STUDY_QUEUE_OPEN_STORAGE_KEY = 'insight-engine.note-study-queue-open';
export const NOTE_WIKI_EXPLORE_OPEN_STORAGE_KEY = 'insight-engine.note-wiki-explore-open';

const NOTE_STUDY_CARD_PRIORITY: NoteStudyCardKind[] = [
  'review-needed',
  'study-start',
  'completed',
  'recent',
];

export function getNoteStudyCardOrder(
  counts: Record<NoteStudyCardKind, number>
): NoteStudyCardKind[] {
  return NOTE_STUDY_CARD_PRIORITY.filter((kind) => counts[kind] > 0);
}

export function getNoteStudyQueueCount(counts: Record<NoteStudyCardKind, number>): number {
  return getNoteStudyCardOrder(counts).reduce((sum, kind) => sum + counts[kind], 0);
}

export function serializeNotePanelOpen(open: boolean): string {
  return open ? 'open' : 'closed';
}

export function parseNotePanelOpen(value: string | null, fallback = true): boolean {
  if (value === 'open') return true;
  if (value === 'closed') return false;
  return fallback;
}

export function serializeNoteStudyQueueOpen(open: boolean): string {
  return serializeNotePanelOpen(open);
}

export function parseNoteStudyQueueOpen(value: string | null, fallback = true): boolean {
  return parseNotePanelOpen(value, fallback);
}

export function getNoteStudyCounts(note: NoteListItem): NoteStudyCounts {
  return {
    learning: note.learning_point_count ?? 0,
    review: note.review_question_count ?? 0,
  };
}

export function getNoteStudyStatus(
  note: NoteListItem,
  progress?: NoteStudyProgress
): NoteStudyStatus {
  const summary = getNoteStudySummary(
    progress ?? { learning: [], review: [], updatedAt: null },
    getNoteStudyCounts(note)
  );
  if (summary.total === 0 || summary.completed === 0) return 'not-started';
  if (summary.completed >= summary.total) return 'completed';
  return 'in-progress';
}

export function getNoteStudyStatusLabel(status: NoteStudyStatus): string {
  if (status === 'completed') return '완료';
  if (status === 'in-progress') return '진행중';
  return '미시작';
}

export function getNoteStudyStatusCounts(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>
): Record<NoteStudyStatus, number> {
  return notes.reduce<Record<NoteStudyStatus, number>>(
    (counts, note) => {
      const status = getNoteStudyStatus(note, progressByNote[note.id]);
      counts[status] += 1;
      return counts;
    },
    { 'not-started': 0, 'in-progress': 0, completed: 0 }
  );
}

export function filterNotesByStudyStatus(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  status: NoteStudyStatus | null
): NoteListItem[] {
  if (!status) return notes;
  return notes.filter((note) => getNoteStudyStatus(note, progressByNote[note.id]) === status);
}

function getStudyResumeItem(
  note: NoteListItem,
  progressByNote: Record<string, NoteStudyProgress>
): NoteStudyResumeItem {
  const progress = progressByNote[note.id];
  const summary = getNoteStudySummary(
    progress ?? { learning: [], review: [], updatedAt: null },
    getNoteStudyCounts(note)
  );
  return { note, summary, updatedAt: progress?.updatedAt ?? null };
}

export function getNotesWithStudyProgress(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  limit = 3
): NoteStudyResumeItem[] {
  return notes
    .map((note) => getStudyResumeItem(note, progressByNote))
    .filter((item) => item.summary.total > 0 && item.summary.completed > 0)
    .sort((a, b) => {
      const timeA = a.updatedAt ? Date.parse(a.updatedAt) : 0;
      const timeB = b.updatedAt ? Date.parse(b.updatedAt) : 0;
      return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA);
    })
    .slice(0, limit);
}

export function getNotesNeedingReview(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  limit = 3
): NoteStudyResumeItem[] {
  return notes
    .map((note) => getStudyResumeItem(note, progressByNote))
    .filter((item) => (
      item.summary.total > 0 &&
      item.summary.completed > 0 &&
      item.summary.completed < item.summary.total
    ))
    .sort((a, b) => {
      if (a.summary.percent !== b.summary.percent) {
        return a.summary.percent - b.summary.percent;
      }
      const timeA = a.updatedAt ? Date.parse(a.updatedAt) : 0;
      const timeB = b.updatedAt ? Date.parse(b.updatedAt) : 0;
      return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA);
    })
    .slice(0, limit);
}

export function getStudyStartCandidates(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  limit = 3
): NoteStudyResumeItem[] {
  return notes
    .map((note) => getStudyResumeItem(note, progressByNote))
    .filter((item) => item.summary.total > 0 && item.summary.completed === 0)
    .sort((a, b) => {
      const timeA = Date.parse(a.note.created_at);
      const timeB = Date.parse(b.note.created_at);
      return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA);
    })
    .slice(0, limit);
}

export function getCompletedStudyItems(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  limit = 3
): NoteStudyResumeItem[] {
  return notes
    .map((note) => getStudyResumeItem(note, progressByNote))
    .filter((item) => item.summary.total > 0 && item.summary.completed >= item.summary.total)
    .sort((a, b) => {
      const timeA = a.updatedAt ? Date.parse(a.updatedAt) : 0;
      const timeB = b.updatedAt ? Date.parse(b.updatedAt) : 0;
      return (Number.isNaN(timeB) ? 0 : timeB) - (Number.isNaN(timeA) ? 0 : timeA);
    })
    .slice(0, limit);
}

export function getRecentStudyResumeItems(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  excludedNoteIds: ReadonlySet<string> = new Set(),
  limit = 3
): NoteStudyResumeItem[] {
  return getNotesWithStudyProgress(notes, progressByNote, notes.length)
    .filter((item) => !excludedNoteIds.has(item.note.id))
    .slice(0, limit);
}

export function getDailyStudyPlanItems(
  notes: NoteListItem[],
  progressByNote: Record<string, NoteStudyProgress>,
  limit = 3
): NoteStudyPlanItem[] {
  const continuing = getNotesNeedingReview(notes, progressByNote, notes.length).map((item) => ({
    ...item,
    kind: 'continue' as const,
    label: '이어 복습',
    actionLabel: '남은 항목 이어가기',
    remaining: item.summary.total - item.summary.completed,
  }));
  const starting = getStudyStartCandidates(notes, progressByNote, notes.length).map((item) => ({
    ...item,
    kind: 'start' as const,
    label: '새로 시작',
    actionLabel: '첫 체크 시작',
    remaining: item.summary.total,
  }));

  return [...continuing, ...starting].slice(0, Math.max(0, limit));
}

function cleanMarkdownValue(value: string | undefined, fallback = '-'): string {
  const cleaned = (value ?? '').replace(/\s+/g, ' ').trim();
  return cleaned || fallback;
}

export function buildDailyStudyPlanMarkdown(
  items: NoteStudyPlanItem[],
  title = '오늘의 복습 플랜'
): string {
  const heading = cleanMarkdownValue(title, '오늘의 복습 플랜');
  if (items.length === 0) {
    return `# ${heading}\n\n복습할 노트가 없습니다.`;
  }

  return [
    `# ${heading}`,
    '',
    ...items.flatMap((item, index) => [
      `${index + 1}. ${cleanMarkdownValue(item.note.title, '제목 없음')}`,
      `   - 단계: ${item.label}`,
      `   - 행동: ${item.actionLabel}`,
      `   - 남은 항목: ${item.remaining}개`,
      `   - 진행: ${item.summary.completed}/${item.summary.total} (${item.summary.percent}%)`,
      `   - 링크: /notes/${encodeURIComponent(item.note.id)}#study-progress`,
    ]),
  ].join('\n');
}
