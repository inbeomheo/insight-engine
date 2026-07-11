/**
 * SSE(Server-Sent Events) 스트림을 파싱하여 이벤트를 콜백으로 전달합니다.
 * generateStream에서 사용합니다.
 */
export async function parseSSEStream<T>(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: T) => void,
  signal?: AbortSignal,
  onNetworkError?: () => void
): Promise<void> {
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event: T = JSON.parse(line.slice(6));
            onEvent(event);
          } catch {
            // JSON 파싱 실패 무시
          }
        }
      }
    }
  } catch {
    if (signal?.aborted) return;
    onNetworkError?.();
  }
}
