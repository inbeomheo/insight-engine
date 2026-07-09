import type { NoteOutlineItem } from './note-outline';
import type { NoteStudySummary } from './note-study-progress';

export interface NoteWikiBriefInput {
  sourceType?: string;
  outlineItems: NoteOutlineItem[];
  studySummary: Pick<NoteStudySummary, 'completed' | 'total' | 'percent'>;
  quoteCount: number;
  relatedNoteCount: number;
  hasLinkedReport: boolean;
}

export interface NoteWikiBriefItem {
  label: string;
  value: string;
  description: string;
}

export interface NoteWikiQuickAction {
  href: string;
  label: string;
}

export interface NoteWikiReadingPathSource {
  id: string;
  title: string;
  score: number;
  snippet?: string;
}

export interface NoteWikiReadingPathItem {
  id: string;
  href: string;
  title: string;
  label: string;
  description: string;
  scorePercent: number;
}

function getSourceLabel(type?: string): string {
  if (type === 'youtube') return 'YouTube';
  if (type === 'text') return '직접 텍스트';
  if (type === 'article') return 'Article';
  if (type === 'document') return '문서';
  if (type === 'voice') return '음성';
  return '기타';
}

function getStudyValue(summary: NoteWikiBriefInput['studySummary']): string {
  if (summary.total <= 0) return '학습 항목 없음';
  if (summary.completed <= 0) return `미시작 · 0/${summary.total}`;
  if (summary.completed >= summary.total) return `완료 · ${summary.completed}/${summary.total}`;
  return `${summary.percent}% 진행 · ${summary.completed}/${summary.total}`;
}

function getNextActionValue(summary: NoteWikiBriefInput['studySummary']): string {
  if (summary.total <= 0) return '근거 Q&A로 확장';
  if (summary.completed <= 0) return '복습 시작';
  if (summary.completed >= summary.total) return '전체 완료';
  return `남은 ${summary.total - summary.completed}개`;
}

export function buildNoteWikiBrief(input: NoteWikiBriefInput): NoteWikiBriefItem[] {
  const evidenceCount =
    Math.max(0, input.quoteCount) +
    Math.max(0, input.relatedNoteCount) +
    (input.hasLinkedReport ? 1 : 0);

  return [
    {
      label: '출처',
      value: getSourceLabel(input.sourceType),
      description: '이 문서가 만들어진 원본 유형',
    },
    {
      label: '문서 구성',
      value: `${Math.max(0, input.outlineItems.length)}개 섹션`,
      description: '목차로 이동 가능한 지식 블록',
    },
    {
      label: '학습 상태',
      value: getStudyValue(input.studySummary),
      description: '체크한 학습 포인트와 복습 질문',
    },
    {
      label: '다음 행동',
      value: getNextActionValue(input.studySummary),
      description: '지금 이어갈 학습 단계',
    },
    {
      label: '근거 연결',
      value: evidenceCount > 0 ? `${evidenceCount}개 연결` : '연결 없음',
      description: '원본 결과·관련 노트·인용 근거',
    },
  ];
}

export function buildNoteWikiQuickActions(input: NoteWikiBriefInput): NoteWikiQuickAction[] {
  const actions: NoteWikiQuickAction[] = [];

  if (input.studySummary.total > 0 && input.studySummary.completed < input.studySummary.total) {
    actions.push({
      href: '#study-progress',
      label: input.studySummary.completed > 0 ? '이어 복습' : '복습 시작',
    });
  }

  actions.push({ href: '#chat', label: '근거 Q&A' });

  if (input.relatedNoteCount > 0) {
    actions.push({ href: '#wiki-reading-path', label: '읽기 경로' });
  }
  if (input.quoteCount > 0) {
    actions.push({ href: '#quotes', label: '인용 보기' });
  }

  return actions.slice(0, 4);
}

export function buildNoteWikiReadingPath(
  relatedNotes: NoteWikiReadingPathSource[] = [],
  limit = 3
): NoteWikiReadingPathItem[] {
  return [...relatedNotes]
    .filter((note) => note.id)
    .sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return (a.title || '').localeCompare(b.title || '');
    })
    .slice(0, Math.max(0, limit))
    .map((note, index) => ({
      id: note.id,
      href: `/notes/${encodeURIComponent(note.id)}`,
      title: note.title || '제목 없음',
      label: index === 0 ? '다음 읽기' : `${index + 1}번째 연결`,
      description: note.snippet?.trim() || '현재 문서와 의미가 가까운 관련 노트입니다.',
      scorePercent: Math.round(Math.max(0, Math.min(1, note.score)) * 100),
    }));
}
