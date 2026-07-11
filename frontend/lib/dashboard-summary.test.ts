import { describe, expect, it } from 'vitest';
import { buildLocalDashboardMarkdown, buildLocalDashboardStats, cleanMarkdownLine } from './dashboard-summary';
import type { Report } from './types';

function makeReport(partial: Partial<Report>): Report {
  return {
    id: 'r1',
    url: '',
    youtube_title: '',
    title: '제목',
    content: '본문',
    html: '<p>본문</p>',
    style: 'summary',
    prompt: '',
    usage: { total_tokens: 0 },
    elapsed_time: 0,
    transcript_source: 'text',
    cached: false,
    comment_summary_included: false,
    time: '오전 10:00',
    createdAt: new Date(2026, 6, 10, 10).getTime(),
    ...partial,
  };
}

describe('dashboard-summary', () => {
  it('로컬 결과 통계와 최근 7일 흐름을 만든다', () => {
    const today = new Date(2026, 6, 10, 12);
    const reports = [
      makeReport({ id: 'today', title: '오늘', style: 'summary', content: '12345', usage: { total_tokens: 100 }, createdAt: today.getTime() }),
      makeReport({
        id: 'yesterday',
        title: '어제',
        style: 'qna',
        content: '123',
        usage: { total_tokens: 50 },
        createdAt: new Date(2026, 6, 9, 9).getTime(),
        knowledge_note_id: 'note-yesterday',
        knowledge_note_title: '어제 학습 노트',
        knowledge_note_saved_at: '2026-07-10T01:00:00Z',
      }),
      makeReport({
        id: 'old',
        title: '오래됨',
        style: 'summary',
        content: '12',
        usage: { total_tokens: 25 },
        createdAt: new Date(2026, 6, 1, 9).getTime(),
      }),
    ];

    const stats = buildLocalDashboardStats(reports, new Set(['yesterday']), 20, today);

    expect(stats.totalTokens).toBe(175);
    expect(stats.avgLength).toBe(3);
    expect(stats.topStyles[0]).toEqual(['summary', 2]);
    expect(stats.recent.map((report) => report.id)).toEqual(['today', 'yesterday', 'old']);
    expect(stats.pinned.map((report) => report.id)).toEqual(['yesterday']);
    expect(stats.linkedNoteCount).toBe(1);
    expect(stats.linkedNotes.map((report) => report.id)).toEqual(['yesterday']);
    expect(stats.activityDays.map((day) => day.count)).toEqual([0, 0, 0, 0, 0, 1, 1]);
    expect(stats.storageStatus).toBe('여유 있음');
  });

  it('Markdown 요약에 고정 결과와 활동 흐름을 포함한다', () => {
    const now = new Date(2026, 6, 10, 12);
    const report = makeReport({
      id: 'pinned',
      title: '  고정   결과  ',
      style: 'quiz',
      url: 'https://example.com',
      knowledge_note_id: 'note-pinned',
      knowledge_note_title: '고정 결과 노트',
      knowledge_note_saved_at: '2026-07-10T01:00:00Z',
      createdAt: now.getTime(),
    });
    const stats = buildLocalDashboardStats([report], new Set(['pinned']), 20, now);

    const markdown = buildLocalDashboardMarkdown(stats, 1, 20, now);

    expect(markdown).toContain('# 내 작업 요약');
    expect(markdown).toContain('## 최근 7일 생성 흐름');
    expect(markdown).toContain('## 고정 결과');
    expect(markdown).toContain('## 연결된 학습 노트');
    expect(markdown).toContain('고정 결과');
    expect(markdown).toContain('/notes/note-pinned');
    expect(markdown).toContain('https://example.com');
  });

  it('Markdown 한 줄 값을 정리한다', () => {
    expect(cleanMarkdownLine('  여러\n줄\t값  ')).toBe('여러 줄 값');
    expect(cleanMarkdownLine('', '대체')).toBe('대체');
  });
});
