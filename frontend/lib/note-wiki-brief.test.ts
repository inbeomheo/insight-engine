import { describe, expect, it } from 'vitest';
import {
  buildNoteChatSuggestedQuestions,
  buildNoteQuoteMarkdown,
  buildNoteWikiBrief,
  buildNoteWikiQuickActions,
  buildNoteWikiReadingPath,
  buildNoteWikiReadingPathMarkdown,
} from './note-wiki-brief';

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
      { label: '다음 행동', value: '남은 3개', description: '지금 이어갈 학습 단계' },
      { label: '근거 연결', value: '5개 연결', description: '원본 결과·관련 노트·인용 근거' },
    ]);
  });

  it('summarizes the next action for unstarted, completed, or non-study notes', () => {
    const base = {
      sourceType: 'text',
      outlineItems: [],
      quoteCount: 0,
      relatedNoteCount: 0,
      hasLinkedReport: false,
    };

    expect(buildNoteWikiBrief({ ...base, studySummary: { completed: 0, total: 2, percent: 0 } })[3].value).toBe('복습 시작');
    expect(buildNoteWikiBrief({ ...base, studySummary: { completed: 2, total: 2, percent: 100 } })[3].value).toBe('전체 완료');
    expect(buildNoteWikiBrief({ ...base, studySummary: { completed: 0, total: 0, percent: 0 } })[3].value).toBe('근거 Q&A로 확장');
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

  it('moves completed study notes to evidence expansion actions', () => {
    expect(
      buildNoteWikiQuickActions({
        sourceType: 'youtube',
        outlineItems: [],
        studySummary: { completed: 3, total: 3, percent: 100 },
        quoteCount: 1,
        relatedNoteCount: 1,
        hasLinkedReport: true,
      })
    ).toEqual([
      { href: '#chat', label: '근거 Q&A' },
      { href: '#wiki-reading-path', label: '읽기 경로' },
      { href: '#quotes', label: '인용 보기' },
    ]);
  });

  it('builds a ranked wiki reading path from related notes', () => {
    expect(
      buildNoteWikiReadingPath([
        { id: 'low score', title: '낮은 관련', score: 0.2, snippet: '' },
        { id: 'high-score', title: '높은 관련', score: 0.94, snippet: '핵심 연결 설명' },
        { id: '', title: '잘못된 노트', score: 1 },
        { id: 'over-score', title: '상한 보정', score: 1.7, snippet: '상한 확인' },
      ], 2)
    ).toEqual([
      {
        id: 'over-score',
        href: '/notes/over-score',
        title: '상한 보정',
        label: '다음 읽기',
        description: '상한 확인',
        scorePercent: 100,
      },
      {
        id: 'high-score',
        href: '/notes/high-score',
        title: '높은 관련',
        label: '2번째 연결',
        description: '핵심 연결 설명',
        scorePercent: 94,
      },
    ]);
  });

  it('builds markdown for the wiki reading path', () => {
    const items = buildNoteWikiReadingPath([
      { id: 'next', title: '다음 [문서]', score: 0.84, snippet: '  핵심\n연결  ' },
      { id: 'fallback', title: '', score: 0.4 },
    ]);

    expect(buildNoteWikiReadingPathMarkdown(items, '현재 노트')).toBe([
      '# 위키 읽기 경로: 현재 노트',
      '',
      '1. [다음 \\[문서\\]](/notes/next)',
      '   - 단계: 다음 읽기',
      '   - 관련도: 84%',
      '   - 이유: 핵심 연결',
      '2. [제목 없음](/notes/fallback)',
      '   - 단계: 2번째 연결',
      '   - 관련도: 40%',
      '   - 이유: 현재 문서와 의미가 가까운 관련 노트입니다.',
    ].join('\n'));

    expect(buildNoteWikiReadingPathMarkdown([], '')).toBe(
      '# 위키 읽기 경로: 현재 문서\n\n연결된 관련 문서가 없습니다.'
    );
  });

  it('builds markdown for quote evidence', () => {
    expect(
      buildNoteQuoteMarkdown([
        { text: '  핵심\n근거  ', ref: '  01:23  ' },
        { text: '', ref: '' },
      ], '  인용\n묶음  ')
    ).toBe([
      '# 인용 묶음',
      '',
      '1. "핵심 근거" (01:23)',
      '2. "인용 내용 없음"',
    ].join('\n'));

    expect(buildNoteQuoteMarkdown([], '')).toBe(
      '# 근거 인용\n\n인용 가능한 근거가 없습니다.'
    );
  });

  it('builds suggested questions for evidence-based note chat', () => {
    expect(buildNoteChatSuggestedQuestions({
      quoteCount: 2,
      relatedNoteCount: 1,
      studySummary: { completed: 1, total: 3, percent: 33 },
    })).toEqual([
      '이 노트의 핵심 근거를 3개로 요약해줘.',
      '근거 인용을 기준으로 중요한 주장과 출처를 짝지어줘.',
      '남은 학습 항목을 복습 질문으로 다시 정리해줘.',
    ]);

    expect(buildNoteChatSuggestedQuestions({
      quoteCount: 0,
      relatedNoteCount: 0,
      studySummary: { completed: 0, total: 0, percent: 0 },
    })).toEqual(['이 노트의 핵심 근거를 3개로 요약해줘.']);
  });
});
