import type { NoteSource } from './api';
import type { Report } from './types';

export function getKnowledgeNoteSource(report: Report): NoteSource | null {
  const title =
    report.source_title ||
    report.youtube_title ||
    report.title ||
    (report.transcript_source === 'direct_input' ? '직접 입력 텍스트' : '학습 소스');

  if (report.url) {
    return {
      type: /(?:youtube\.com|youtu\.be)/i.test(report.url) ? 'youtube' : 'article',
      url: report.url,
      title,
    };
  }

  if (report.source_type === 'text' || report.transcript_source === 'direct_input') {
    return {
      type: 'text',
      url: '',
      title: title || '직접 입력 텍스트',
    };
  }

  return null;
}

export function getKnowledgeNoteContent(report: Report): string {
  return report.transcript?.trim() || report.content;
}

export function findReportLinkedToNote(reports: Report[], noteId: string): Report | null {
  const targetNoteId = noteId.trim();
  if (!targetNoteId) return null;

  return reports.find((report) => report.knowledge_note_id === targetNoteId) ?? null;
}
