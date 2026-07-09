import { describe, expect, it } from 'vitest';
import { buildNoteWikiBrief, buildNoteWikiQuickActions } from './note-wiki-brief';

describe('note-wiki-brief', () => {
  it('summarizes source, structure, study progress, and evidence links', () => {
    const input = {
      sourceType: 'youtube',
      outlineItems: [
        { id: 'source', label: '출처' },
        { id: 'wiki-brief', label: '문서 브리핑' },
        { id: 'chat', label: '근거 Q&A' },
      ],
      studySummary: { completed: 2, total: 5, percent: 40 },
      quoteCount: 3,
      relatedNoteCount: 1,
      hasLinkedReport: true,
    };

    expect(buildNoteWikiBrief(input)).toEqual([
      { label: '출처', value: 'YouTube', description: '이 문서가 만들어진 원본 유형' },
      { label: '문서 구성', value: '3개 섹션', description: '목차로 이동 가능한 지식 블록' },
      { label: '학습 상태', value: '40% 진행 · 2/5', description: '체크한 학습 포인트와 복습 질문' },
      { label: '근거 연결', value: '5개 연결', description: '원본 결과·관련 노트·인용 근거' },
    ]);
  });

  it('builds quick actions based on available wiki sections', () => {
    expect(
      buildNoteWikiQuickActions({
        sourceType: 'text',
        outlineItems: [],
        studySummary: { completed: 0, total: 2, percent: 0 },
        quoteCount: 1,
        relatedNoteCount: 0,
        hasLinkedReport: false,
      })
    ).toEqual([
      { href: '#study-progress', label: '복습 시작' },
      { href: '#chat', label: '근거 Q&A' },
      { href: '#quotes', label: '인용 보기' },
    ]);
  });
});
