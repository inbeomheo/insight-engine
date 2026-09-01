import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, describe, expect, it } from 'vitest';
import ChatMessage from './ChatMessage';
import type { ChatMessage as ChatMessageType } from '../hooks/useAgentChat';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

let root: Root | null = null;

afterEach(async () => {
  if (root) await act(async () => root!.unmount());
  root = null;
  document.body.innerHTML = '';
});

async function renderMessage(role: ChatMessageType['role'], content: string) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <ChatMessage
        message={{ id: 'message-1', role, content, createdAt: Date.now() }}
      />,
    );
  });
  return container;
}

describe('ChatMessage security', () => {
  it('renders user supplied HTML as inert text', async () => {
    const container = await renderMessage('user', '<img src=x onerror="window.__xss=1"><script>alert(1)</script>');

    expect(container.querySelector('img')).toBeNull();
    expect(container.querySelector('script')).toBeNull();
    expect(container.textContent).toContain('<img src=x');
    expect(container.textContent).toContain('<script>alert(1)</script>');
  });

  it('renders assistant markdown but never raw HTML', async () => {
    const container = await renderMessage(
      'assistant',
      '**안전한 강조**\n\n<img src=x onerror="window.__xss=1">',
    );

    expect(container.querySelector('strong')?.textContent).toBe('안전한 강조');
    expect(container.querySelector('img')).toBeNull();
    expect(container.innerHTML).not.toContain('onerror');
  });
});
