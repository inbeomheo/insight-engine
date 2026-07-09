import { describe, expect, it } from 'vitest';
import { createReport } from './report-factory';
import {
  findReportLinkedToNote,
  getKnowledgeNoteContent,
  getKnowledgeNotePreview,
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

  it('builds a learning preview before saving a note', () => {
    const report = createReport({
      url: '',
      source_type: 'text',
      source_title: 'Next.js RAG 학습',
      title: 'RAG 노트',
      content: [
        '## RAG 검색',
        'RAG는 지식 검색과 생성 답변을 연결합니다.',
        '복습 질문을 만들면 학습 유지에 도움이 됩니다.',
      ].join('\n'),
      html: '<p>RAG는 지식 검색과 생성 답변을 연결합니다.</p>',
      style: 'summary',
      transcript_source: 'direct_input',
    });

    const preview = getKnowledgeNotePreview(report);

    expect(preview.title).toBe('Next.js RAG 학습');
    expect(preview.sourceLabel).toBe('직접 텍스트');
    expect(preview.tags).toEqual(expect.arrayContaining(['직접 텍스트', '요약', '직접 입력']));
    expect(preview.concepts).toEqual(expect.arrayContaining(['Next.js', 'RAG']));
    expect(preview.learningPoints[0]).toContain('RAG는');
    expect(preview.excerpt).toContain('지식 검색');
  });
});
