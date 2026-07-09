import { describe, expect, it } from 'vitest';
import { createReport } from './report-factory';
import { getKnowledgeNoteContent, getKnowledgeNoteSource } from './knowledge-note-source';

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
});
