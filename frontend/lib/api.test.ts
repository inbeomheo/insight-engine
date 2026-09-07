import { afterEach, describe, expect, it, vi } from 'vitest';
import { clearCache, downloadNotebookLmArtifact, fetchProviders, generate, synthesizeTts, uploadKnowledge } from './api';

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function pendingFetchUntilAborted() {
  return vi.fn().mockImplementation((_url: string, init?: RequestInit) => (
    new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => {
        reject(new DOMException('aborted', 'AbortError'));
      }, { once: true });
    })
  ));
}

function pendingBodyUntilAborted(kind: 'json' | 'blob') {
  return vi.fn().mockImplementation((_url: string, init?: RequestInit) => (
    Promise.resolve({
      ok: true,
      [kind]: () => new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => {
          reject(new DOMException('aborted', 'AbortError'));
        }, { once: true });
      }),
    })
  ));
}

describe('응답 본문 수신 중 시간 제한과 취소', () => {
  it('헤더가 도착했어도 JSON 본문이 멈추면 시간 초과를 반환한다', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', pendingBodyUntilAborted('json'));
    const failure = fetchProviders().catch((error: unknown) => error);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(await failure).toEqual(expect.objectContaining({
      message: expect.stringContaining('10초'),
    }));
    expect(vi.getTimerCount()).toBe(0);
  });

  it('파일 본문이 멈추면 다운로드 제한 시간이 적용된다', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', pendingBodyUntilAborted('blob'));
    const failure = downloadNotebookLmArtifact('test-artifact').catch((error: unknown) => error);
    await vi.advanceTimersByTimeAsync(600_000);
    expect(await failure).toEqual(expect.objectContaining({
      message: expect.stringContaining('600초'),
    }));
    expect(vi.getTimerCount()).toBe(0);
  });

  it('파일 본문 수신 중 사용자가 취소하면 즉시 중단한다', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', pendingBodyUntilAborted('blob'));
    const controller = new AbortController();
    const failure = downloadNotebookLmArtifact('test-artifact', controller.signal)
      .catch((error: unknown) => error);
    await vi.advanceTimersByTimeAsync(0);
    controller.abort();
    expect(await failure).toEqual(expect.objectContaining({ name: 'AbortError' }));
    expect(vi.getTimerCount()).toBe(0);
  });
});

describe('clearCache', () => {
  it('전체 삭제 의도를 명시해 백엔드의 안전한 캐시 계약을 지킨다', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({ success: true, deleted: 0 }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await clearCache();

    expect(fetchMock).toHaveBeenCalledWith('/api/cache', expect.objectContaining({
      method: 'DELETE',
      body: JSON.stringify({ scope: 'all' }),
    }));
  });
});

describe('billable POST idempotency', () => {
  it('각 사용자 작업에는 새 키를 만들고 인증 재시도 가능한 요청 헤더에 싣는다', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });
    vi.stubGlobal('fetch', fetchMock);

    const request = {
      url: 'https://example.com/video',
      model: 'test',
      style: 'blog',
      modifiers: { length: 'medium' as const, writing_style: 'explanatory' as const },
    };
    await generate(request);
    await generate(request);

    const firstKey = new Headers(fetchMock.mock.calls[0][1].headers).get('Idempotency-Key');
    const secondKey = new Headers(fetchMock.mock.calls[1][1].headers).get('Idempotency-Key');
    expect(firstKey).toMatch(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/);
    expect(secondKey).not.toBe(firstKey);
  });
});

describe('long-running upload timeouts', () => {
  it('지식 파일 업로드를 120초 뒤 중단하고 FormData boundary는 브라우저에 맡긴다', async () => {
    vi.useFakeTimers();
    const fetchMock = pendingFetchUntilAborted();
    vi.stubGlobal('fetch', fetchMock);

    const upload = uploadKnowledge(new File(['knowledge'], 'knowledge.txt'));
    const failure = upload.catch((error: unknown) => error);
    await vi.advanceTimersByTimeAsync(120_000);

    expect(await failure).toEqual(expect.objectContaining({ message: expect.stringContaining('120초') }));
    const headers = new Headers(fetchMock.mock.calls[0][1]?.headers);
    expect(headers.has('Content-Type')).toBe(false);
  });

  it('TTS 요청을 300초 뒤 중단한다', async () => {
    vi.useFakeTimers();
    const fetchMock = pendingFetchUntilAborted();
    vi.stubGlobal('fetch', fetchMock);

    const synthesis = synthesizeTts('테스트');
    const failure = synthesis.catch((error: unknown) => error);
    await vi.advanceTimersByTimeAsync(300_000);

    expect(await failure).toEqual(expect.objectContaining({ message: expect.stringContaining('300초') }));
  });
});
