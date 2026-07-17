export type ApiError<T = unknown> = Error & {
  status?: number;
  body?: T;
};

export interface HttpRequestOptions {
  timeoutMs?: number;
  timeoutMessage?: string;
}

const DEFAULT_TIMEOUT_MS = 30_000;

export function isApiError<T = unknown>(error: unknown): error is ApiError<T> {
  return error instanceof Error && ('status' in error || 'body' in error);
}

function isFormDataBody(body: BodyInit | null | undefined): body is FormData {
  return typeof FormData !== 'undefined' && body instanceof FormData;
}

function buildHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);
  if (!isFormDataBody(init?.body) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  return headers;
}

async function parseErrorResponse(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { error: text };
  }
}

function errorMessage(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'error' in body) {
    const message = (body as { error?: unknown }).error;
    if (typeof message === 'string' && message.trim()) return message;
  }
  return `HTTP ${status}`;
}

function createApiError(body: unknown, status: number): ApiError {
  const error = new Error(errorMessage(body, status)) as ApiError;
  error.status = status;
  error.body = body;
  return error;
}

function isAbortError(error: unknown): boolean {
  return Boolean(
    error
      && typeof error === 'object'
      && 'name' in error
      && error.name === 'AbortError',
  );
}

async function requestWithParser<T>(
  url: string,
  init: RequestInit | undefined,
  parse: (response: Response) => Promise<T>,
  options: HttpRequestOptions,
): Promise<T> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  let timedOut = false;

  const abortFromCaller = () => controller.abort(init?.signal?.reason);
  if (init?.signal?.aborted) {
    abortFromCaller();
  } else {
    init?.signal?.addEventListener('abort', abortFromCaller, { once: true });
  }

  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch(url, {
      ...init,
      headers: buildHeaders(init),
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await parseErrorResponse(response);
      throw createApiError(body, response.status);
    }
    return parse(response);
  } catch (error) {
    if (timedOut && isAbortError(error)) {
      throw new Error(
        options.timeoutMessage
          ?? `요청 시간이 초과되었습니다 (${Math.round(timeoutMs / 1000)}초). 네트워크 상태를 확인하거나 다시 시도해주세요.`,
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
    init?.signal?.removeEventListener('abort', abortFromCaller);
  }
}

export function requestJson<T>(
  url: string,
  init?: RequestInit,
  options: HttpRequestOptions = {},
): Promise<T> {
  return requestWithParser(url, init, (response) => response.json() as Promise<T>, options);
}

export function requestBlob(
  url: string,
  init?: RequestInit,
  options: HttpRequestOptions = {},
): Promise<Blob> {
  return requestWithParser(url, init, (response) => response.blob(), options);
}
