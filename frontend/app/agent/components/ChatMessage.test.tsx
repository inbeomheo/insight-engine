import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import ChatMessage from './ChatMessage';

describe('ChatMessage', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    container.remove();
  });

  it('에이전트가 보낸 raw HTML을 실행 가능한 DOM으로 삽입하지 않는다', async () => {
    await act(async () => {
      root.render(
        <ChatMessage
          message={{
            id: 'message-1',
            role: 'assistant',
            content: '<img src=x onerror="localStorage.clear()"> **안전한 답변**',
            createdAt: 1,
          }}
        />,
      );
    });

    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('strong')?.textContent).toBe('안전한 답변');
    expect(container.textContent).toContain('<img src=x');
  });
});
