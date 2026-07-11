import { describe, expect, it } from 'vitest';
import { responseToReport } from './report-factory';
import type { GenerateResponse } from './types';

describe('responseToReport', () => {
  it('source_receipts를 Report로 전달한다', () => {
    const response = {
      title: '제목',
      content: '본문 [01:00]',
      html: '<p>본문</p>',
      usage: { total_tokens: 10 },
      elapsed_time: 1,
      transcript_source: 'youtube',
      prompt: 'prompt',
      cached: false,
      comment_summary_included: false,
      source_receipts: [{
        claim: '본문',
        marker: '[01:00]',
        seconds: 60,
        timestamp_url: 'https://youtube.com/watch?v=dQw4w9WgXcQ&t=60s',
        collected_at: '2026-07-08T00:00:00+00:00',
        valid: true,
        source: { type: 'youtube', video_id: 'dQw4w9WgXcQ', title: '영상' },
      }],
    } satisfies GenerateResponse;

    const report = responseToReport(response, 'https://youtu.be/dQw4w9WgXcQ', 'summary');

    expect(report.source_receipts).toHaveLength(1);
    expect(report.source_receipts?.[0]).toEqual(response.source_receipts[0]);
  });
});
