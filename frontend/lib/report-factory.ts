import type { Report, GenerateResponse, TokenUsage } from './types';
import { formatTime } from './helpers';

type ReportInput = Partial<Report> & {
  url: string;
  title: string;
  content: string;
  html: string;
  style: string;
};

/**
 * Report 객체를 생성합니다.
 * 기본값을 제공하여 각 생성 모드(단일, 배치, 병합, 퓨전, 파이프라인)에서
 * 중복 코드 없이 Report를 만들 수 있습니다.
 */
export function createReport(input: ReportInput): Report {
  return {
    id: crypto.randomUUID(),
    youtube_title: '',
    prompt: '',
    usage: { total_tokens: 0 },
    elapsed_time: 0,
    transcript_source: '',
    cached: false,
    comment_summary_included: false,
    time: formatTime(),
    createdAt: Date.now(),
    ...input,
  };
}

/**
 * GenerateResponse를 Report로 변환합니다.
 * 단일 생성, 배치 생성의 개별 결과에서 사용합니다.
 */
export function responseToReport(
  res: GenerateResponse,
  url: string,
  style: string,
  overrides?: Partial<Report>
): Report {
  return createReport({
    url,
    youtube_title: res.youtube_title || '',
    title: res.title,
    content: res.content,
    html: res.html,
    style,
    prompt: res.prompt || '',
    usage: res.usage || { total_tokens: 0 },
    elapsed_time: res.elapsed_time || 0,
    transcript_source: res.transcript_source || '',
    cached: res.cached || false,
    comment_summary_included: res.comment_summary_included || false,
    seo: res.seo,
    geo: res.geo,
    faq_schema: res.faq_schema,
    cta: res.cta,
    json_ld_schemas: res.json_ld_schemas,
    web_sources: res.web_sources,
    transcript_segments: res.transcript_segments,
    chapters: res.chapters,
    ...overrides,
  });
}
