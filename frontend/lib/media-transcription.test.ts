import { afterEach, describe, expect, it, vi } from 'vitest';

import { extractMedia } from './api';

describe('media transcription API polling', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('polls a queued job and returns the timed transcript', async () => {
    vi.useFakeTimers();
    const responses = [
      new Response(JSON.stringify({
        job_id: 'job-1', status: 'queued', stage: 'uploaded', progress: 0,
      }), { status: 202, headers: { 'Content-Type': 'application/json' } }),
      new Response(JSON.stringify({
        job_id: 'job-1', status: 'running', stage: 'transcribing', progress: 30,
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
      new Response(JSON.stringify({
        job_id: 'job-1', status: 'succeeded', stage: 'ready', progress: 100,
        source_type: 'video', source_title: '회의',
        result: {
          text: '전사 결과', transcript_source: 'whisper', detected_language: 'ko',
          transcript_segments: [{ start: 0, end: 1.5, text: '전사 결과' }],
        },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    ];
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => responses.shift()!);

    const pending = extractMedia(new File(['video'], '회의.mp4', { type: 'video/mp4' }));
    await vi.advanceTimersByTimeAsync(1500);
    const result = await pending;

    expect(result.source_type).toBe('video');
    expect(result.transcript_segments[0]).toEqual({ start: 0, end: 1.5, text: '전사 결과' });
    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });

  it('surfaces a worker failure message', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify({
        job_id: 'job-2', status: 'queued', stage: 'uploaded', progress: 0,
      }), { status: 202, headers: { 'Content-Type': 'application/json' } }))
      .mockResolvedValueOnce(new Response(JSON.stringify({
        job_id: 'job-2', status: 'failed', stage: 'normalizing', progress: 100,
        error: { code: 'MEDIA_INVALID', message: '오디오 트랙이 없습니다.', retryable: false },
      }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    await expect(extractMedia(new File(['video'], '무음.mp4')))
      .rejects.toThrow('오디오 트랙이 없습니다.');
  });
});
