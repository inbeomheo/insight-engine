import { act, type ComponentProps } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { askResultChat } from '@/lib/api';
import ResultChatPanel from './ResultChatPanel';

vi.mock('@/lib/api', () => ({
  askResultChat: vi.fn(),
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}));

let root: Root | null = null;
let container: HTMLDivElement | null = null;

async function renderPanel(props: Partial<ComponentProps<typeof ResultChatPanel>> = {}) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <ResultChatPanel
        context="자막 본문"
        model="chatmock/gpt-5.4-mini"
        {...props}
      />
    );
  });
}

async function openPanel() {
  const button = Array.from(document.querySelectorAll('button')).find((el) =>
    el.textContent?.includes('콘텐츠 Q&A'),
  );
  if (!button) throw new Error('open button not found');
  await act(async () => {
    button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

async function submitQuestion(text: string) {
  const textarea = document.querySelector('textarea');
  const form = document.querySelector('form');
  if (!textarea || !form) throw new Error('chat form not found');
  await act(async () => {
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
    setter?.call(textarea, text);
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await act(async () => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await Promise.resolve();
  });
}

describe('ResultChatPanel rag_sources', () => {
  beforeEach(() => {
    vi.mocked(askResultChat).mockReset();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  afterEach(async () => {
    if (root) {
      await act(async () => root!.unmount());
    }
    container?.remove();
    root = null;
    container = null;
  });

  it('renders rag source tray and sends history without source payloads', async () => {
    vi.mocked(askResultChat)
      .mockResolvedValueOnce({
        answer: '첫 답',
        rag_sources: [{
          type: 'knowledge_note',
          id: 'n1',
          title: '학습 노트',
          score: 0.9,
          snippet: '복습 질문 메모',
        }],
      })
      .mockResolvedValueOnce({ answer: '둘째 답', rag_sources: [] });

    await renderPanel();
    await openPanel();
    await submitQuestion('첫 질문');

    expect(document.body.textContent).toContain('근거 1개');
    expect(document.body.textContent).toContain('학습 노트');
    expect(document.body.textContent).toContain('복습 질문 메모');

    await submitQuestion('둘째 질문');

    expect(vi.mocked(askResultChat).mock.calls[1][0].history).toEqual([
      { role: 'user', content: '첫 질문' },
      { role: 'assistant', content: '첫 답' },
    ]);
  });

  it('falls back to legacy notes as sources', async () => {
    vi.mocked(askResultChat).mockResolvedValueOnce({
      answer: '답변',
      notes: [{ id: 'n2', title: '기존 노트', score: 0.8, snippet: '기존 스니펫' }],
    });

    await renderPanel();
    await openPanel();
    await submitQuestion('질문');

    expect(document.body.textContent).toContain('근거 1개');
    expect(document.body.textContent).toContain('기존 노트');
    expect(document.body.textContent).toContain('기존 스니펫');
  });

  it('fills the input from a suggested question', async () => {
    await renderPanel({
      suggestedQuestions: ['  근거 인용을 기준으로 설명해줘.  ', '', '관련 노트와 비교해줘.'],
    });
    await openPanel();

    const suggestedButton = Array.from(document.querySelectorAll('button')).find((el) =>
      el.textContent?.includes('근거 인용을 기준으로 설명해줘.')
    );
    if (!suggestedButton) throw new Error('suggested question button not found');

    await act(async () => {
      suggestedButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    expect((document.querySelector('textarea') as HTMLTextAreaElement).value).toBe(
      '근거 인용을 기준으로 설명해줘.'
    );
  });

  it('copies an assistant answer as a study card', async () => {
    vi.mocked(askResultChat).mockResolvedValueOnce({
      answer: '핵심 답변',
      rag_sources: [{
        type: 'knowledge_note',
        id: 'n1',
        title: '근거 노트',
        score: 0.92,
        snippet: '근거 스니펫',
      }],
    });

    await renderPanel({ studyCardTitle: '노트 제목' });
    await openPanel();
    await submitQuestion('무엇을 복습할까?');

    const copyButton = Array.from(document.querySelectorAll('button')).find((el) =>
      el.textContent?.includes('복습 카드 복사')
    );
    if (!copyButton) throw new Error('study card copy button not found');

    await act(async () => {
      copyButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await Promise.resolve();
    });

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith([
      '# 근거 Q&A 복습 카드: 노트 제목',
      '',
      '## 질문',
      '무엇을 복습할까?',
      '',
      '## 답변',
      '핵심 답변',
      '',
      '## 근거',
      '1. 근거 노트 · 92% — 근거 스니펫',
    ].join('\n'));
    expect(document.body.textContent).toContain('복사 완료');
  });
});
