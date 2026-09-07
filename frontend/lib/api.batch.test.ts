import { afterEach, describe, expect, it, vi } from 'vitest';
import { generateBatch, generateMerged } from './api';

afterEach(() => vi.unstubAllGlobals());

const urls = ['https://example.com/first', 'https://example.com/second'];
const modifiers = { length: 'medium', writing_style: 'conversational', language: 'ko' } as const;

describe('다중 URL 요청 옵션', () => {
  it('배치 요청 본문에 선택한 상세도·자막 언어·추가 생성 기능을 담는다', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ results: [] }) });
    vi.stubGlobal('fetch', fetchMock);
    await generateBatch(urls, 'test-model', 'summary', modifiers, undefined, {
      detail_level: 'deep', transcript_language: 'ja', enable_web_search: true, enable_agent_mode: true,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain('/generate-batch');
    expect(JSON.parse(init.body)).toEqual({
      urls, model: 'test-model', style: 'summary', modifiers,
      detail_level: 'deep', transcript_language: 'ja', enable_web_search: true, enable_agent_mode: true,
    });
  });

  it('통합 요청 본문에 선택한 자막 언어를 담는다', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal('fetch', fetchMock);
    await generateMerged(urls, 'test-model', 'summary', modifiers, undefined, 'en');

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/generate-merged');
    expect(JSON.parse(init.body)).toMatchObject({ urls, transcript_language: 'en' });
  });
});
