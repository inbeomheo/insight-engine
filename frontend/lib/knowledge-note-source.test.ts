import { describe, expect, it } from 'vitest';
import { createReport } from './report-factory';
import {
  findReportLinkedToNote,
  getKnowledgeNoteContent,
  getKnowledgeNoteSource,
} from './knowledge-note-source';

describe('knowledge-note-source', () => {
  it('builds youtube note source from url reports', () => {
    const report = createReport({
      url: 'https://youtu.be/abc',
      youtube_title: '영상 제목',
      title: '요약 결과',
      content: '생성 결과',
      html: '<p>생성 결과</p>',
      style: 'summary',
    });

    expect(getKnowledgeNoteSource(report)).toEqual({
      type: 'youtube',
      url: 'https://youtu.be/abc',
      title: '영상 제목',
    });
  });

  it('builds text note source without url for direct input reports', () => {
    const report = createReport({
      url: '',
      source_type: 'text',
      source_title: '직접 입력 텍스트',
      title: '요약 결과',
      content: '생성 결과',
      html: '<p>생성 결과</p>',
      style: 'summary',
      transcript: '붙여넣은 원문',
      transcript_source: 'direct_input',
    });

    expect(getKnowledgeNoteSource(report)).toEqual({
      type: 'text',
      url: '',
      title: '직접 입력 텍스트',
    });
    expect(getKnowledgeNoteContent(report)).toBe('붙여넣은 원문');
  });

  it('finds a local report linked to a knowledge note id', () => {
    const reports = [
      createReport({
        id: 'other',
        url: 'https://example.com/other',
        title: '다른 결과',
        content: '다른 내용',
        html: '<p>다른 내용</p>',
        style: 'summary',
      }),
      createReport({
        id: 'linked',
        url: 'https://example.com/source',
        title: '연결된 결과',
        content: '연결된 내용',
        html: '<p>연결된 내용</p>',
        style: 'qna',
        knowledge_note_id: 'note-1',
      }),
    ];

    expect(findReportLinkedToNote(reports, 'note-1')?.id).toBe('linked');
    expect(findReportLinkedToNote(reports, 'missing')).toBeNull();
    expect(findReportLinkedToNote(reports, '   ')).toBeNull();
  });
});
