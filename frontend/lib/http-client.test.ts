import { afterEach, describe, expect, it, vi } from 'vitest';
import { isApiError, requestBlob, requestJson } from './http-client';


afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});


describe('http-client', () => {
  it('adds JSON content type while preserving Headers instances', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await requestJson('/test', {
      method: 'POST',
      headers: new Headers({ 'X-Trace-Id': 'trace-1' }),
      body: JSON.stringify({ value: 1 }),
    });

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(headers.get('X-Trace-Id')).toBe('trace-1');
  });

  it('lets the browser set a multipart boundary for FormData', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const form = new FormData();
    form.append('file', new Blob(['hello']), 'hello.txt');

    await requestJson('/upload', { method: 'POST', body: form });

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.has('Content-Type')).toBe(false);
  });

  it('throws a typed API error with response status and body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: '잘못된 요청', code: 'INVALID' }), {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      }),
    ));

    const error = await requestJson('/failure').catch((caught) => caught);

    expect(isApiError(error)).toBe(true);
    expect(error).toMatchObject({
      message: '잘못된 요청',
      status: 422,
      body: { error: '잘못된 요청', code: 'INVALID' },
    });
  });

  it('preserves plain-text server errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response('gateway unavailable', { status: 503 }),
    ));

    const error = await requestJson('/failure').catch((caught) => caught);

    expect(error).toMatchObject({
      message: 'gateway unavailable',
      status: 503,
      body: { error: 'gateway unavailable' },
    });
  });

  it('distinguishes caller cancellation from an internal timeout', async () => {
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(init.signal?.reason), { once: true });
    }));
    vi.stubGlobal('fetch', fetchMock);
    const controller = new AbortController();
    const request = requestJson('/cancelled', { signal: controller.signal }, { timeoutMs: 60_000 });

    controller.abort();

    await expect(request).rejects.toMatchObject({ name: 'AbortError' });
    await expect(request).rejects.not.toThrow(/시간이 초과/);
  });

  it('reports an internal timeout with the configured message', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn((_url: string, init?: RequestInit) => new Promise((_resolve, reject) => {
      init?.signal?.addEventListener(
        'abort',
        () => reject(new DOMException('aborted', 'AbortError')),
        { once: true },
      );
    }));
    vi.stubGlobal('fetch', fetchMock);
    const request = requestJson('/slow', undefined, {
      timeoutMs: 1_000,
      timeoutMessage: '사용자 지정 시간 초과',
    });
    const assertion = expect(request).rejects.toThrow('사용자 지정 시간 초과');

    await vi.advanceTimersByTimeAsync(1_000);

    await assertion;
  });

  it('parses successful blob responses through the same error pipeline', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response('file-content', { status: 200 }),
    ));

    const result = await requestBlob('/file');

    await expect(result.text()).resolves.toBe('file-content');
  });
});
