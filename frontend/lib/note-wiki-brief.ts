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
      label: '근거 연결',
      value: evidenceCount > 0 ? `${evidenceCount}개 연결` : '연결 없음',
      description: '원본 결과·관련 노트·인용 근거',
    },
  ];
}

export function buildNoteWikiQuickActions(input: NoteWikiBriefInput): NoteWikiQuickAction[] {
  const actions: NoteWikiQuickAction[] = [];

  if (input.studySummary.total > 0) {
    actions.push({
      href: '#study-progress',
      label: input.studySummary.completed > 0 ? '이어 복습' : '복습 시작',
    });
  }

  actions.push({ href: '#chat', label: '근거 Q&A' });

  if (input.relatedNoteCount > 0) {
    actions.push({ href: '#related-notes', label: '관련 노트' });
  }
  if (input.quoteCount > 0) {
    actions.push({ href: '#quotes', label: '인용 보기' });
  }

  return actions.slice(0, 4);
}
