import { afterEach, describe, expect, it, vi } from 'vitest';

import { createKnowledgeNote } from './api';

describe('knowledge note API timeout', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it('keeps note creation alive beyond the default 30 seconds', async () => {
    vi.useFakeTimers();
    let requestSignal: AbortSignal | undefined;

    vi.spyOn(globalThis, 'fetch').mockImplementation((_input, init) => {
      requestSignal = init?.signal ?? undefined;
      return new Promise((_resolve, reject) => {
        requestSignal?.addEventListener('abort', () => {
          reject(new DOMException('Aborted', 'AbortError'));
        });
      });
    });

    const pending = createKnowledgeNote({
      content: '테스트 노트 원문',
      source: { type: 'text', url: '', title: '테스트' },
    });
    const timedOut = expect(pending).rejects.toThrow('요청 시간이 초과되었습니다 (300초)');

    await vi.advanceTimersByTimeAsync(30_000);
    expect(requestSignal?.aborted).toBe(false);

    await vi.advanceTimersByTimeAsync(270_000);
    await timedOut;
    expect(requestSignal?.aborted).toBe(true);
  });
});