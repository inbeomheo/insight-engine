import { describe, expect, it } from 'vitest';
import { transcriptToSrt } from './TranscriptPanel';

describe('transcriptToSrt', () => {
  it('preserves explicit end timestamps', () => {
    expect(transcriptToSrt([
      { start: 1.25, end: 3.5, text: ' 첫 문장 ' },
      { start: 4, end: 7.75, text: '둘째 문장' },
    ])).toBe([
      '1',
      '00:00:01,250 --> 00:00:03,500',
      '첫 문장',
      '',
      '2',
      '00:00:04,000 --> 00:00:07,750',
      '둘째 문장',
    ].join('\n'));
  });

  it('derives a safe end when legacy segments only have start', () => {
    expect(transcriptToSrt([
      { start: 0, text: '첫 구간' },
      { start: 3, text: '둘째 구간' },
    ])).toContain('00:00:00,000 --> 00:00:03,000');
  });
});
