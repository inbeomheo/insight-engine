import type { NoteSource } from './api';
import type { Report } from './types';
import { getStyleLabel } from './helpers';

export interface KnowledgeNotePreview {
  title: string;
  sourceLabel: string;
  contentChars: number;
  concepts: string[];
  tags: string[];
  learningPoints: string[];
  excerpt: string;
}

const STOP_WORDS = new Set([
  '그리고',
  '하지만',
  '합니다',
  '있는',
  '없는',
  '영상',
  '내용',
  '결과',
  '요약',
  '제목',
  '직접',
  '입력',
  '텍스트',
  '생성',
]);

function sourceLabel(source: NoteSource | null): string {
  if (!source) return '학습 자료';
  if (source.type === 'youtube') return 'YouTube';
  if (source.type === 'text') return '직접 텍스트';
  if (source.type === 'article') return '웹 문서';
  if (source.type === 'document') return '문서';
  if (source.type === 'voice') return '음성';
  return '학습 자료';
}

function cleanText(value: string): string {
  return value
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/!\[[^\]]*]\([^)]+\)/g, ' ')
    .replace(/\[([^\]]+)]\([^)]+\)/g, '$1')
    .replace(/[#>*_~|]/g, ' ')
    .replace(/^\s*[-•]\s+/gm, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function truncate(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max).trim()}…` : value;
}

function extractConcepts(text: string): string[] {
  const words = cleanText(text).match(/[가-힣A-Za-z0-9][가-힣A-Za-z0-9+.#-]{1,}/g) ?? [];
  const seen = new Set<string>();
  const concepts: string[] = [];

  for (const word of words) {
    const normalized = word.toLowerCase();
    if (seen.has(normalized)) continue;
    if (STOP_WORDS.has(normalized) || /^\d+$/.test(word) || normalized.startsWith('http')) continue;
    seen.add(normalized);
    concepts.push(word);
    if (concepts.length >= 6) break;
  }

  return concepts;
}

function buildLearningPoints(content: string): string[] {
  const points = content
    .split(/\r?\n/)
    .map(cleanText)
    .filter((line) => line.length >= 18 && !/^(목차|태그|출처)$/i.test(line))
    .map((line) => truncate(line.replace(/^\d+[.)]\s*/, ''), 110))
    .slice(0, 2);

  if (points.length > 0) return points;

  const fallback = cleanText(content);
  return fallback ? [truncate(fallback, 110)] : [];
}

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

export function getKnowledgeNotePreview(report: Report): KnowledgeNotePreview {
  const source = getKnowledgeNoteSource(report);
  const content = getKnowledgeNoteContent(report);
  const label = sourceLabel(source);
  const tags = Array.from(
    new Set(
      [
        label,
        getStyleLabel(report.style),
        report.source_type === 'text' || report.transcript_source === 'direct_input' ? '직접 입력' : '',
      ].filter(Boolean)
    )
  );

  return {
    title: source?.title || report.title || '학습 노트',
    sourceLabel: label,
    contentChars: content.trim().length,
    concepts: extractConcepts(`${source?.title ?? ''} ${report.title} ${content}`),
    tags,
    learningPoints: buildLearningPoints(content),
    excerpt: truncate(cleanText(content), 160),
  };
}
