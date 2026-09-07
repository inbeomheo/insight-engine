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
let execCommandDescriptor: PropertyDescriptor | undefined;

async function renderPanel(props: Partial<ComponentProps<typeof ResultChatPanel>> = {}) {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => {
    root!.render(
      <ResultChatPanel
        context="자막 본문"
        model="cliproxyapi/gpt-5.5"
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

function getStudyCardCopyButtons(): HTMLButtonElement[] {
  return Array.from(document.querySelectorAll('button')).filter((button) =>
    button.textContent?.includes('복습 카드 저장')
  );
}

async function clickStudyCardCopy(button: HTMLButtonElement) {
  await act(async () => {
    button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('ResultChatPanel rag_sources', () => {
  beforeEach(() => {
    vi.mocked(askResultChat).mockReset();
    window.localStorage.clear();
    execCommandDescriptor = Object.getOwnPropertyDescriptor(document, 'execCommand');
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
    if (execCommandDescriptor) {
      Object.defineProperty(document, 'execCommand', execCommandDescriptor);
    } else {
      Reflect.deleteProperty(document, 'execCommand');
    }
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.restoreAllMocks();
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

    await renderPanel({ studyCardTitle: '노트 제목', studyCardSourceHref: '/notes/n1' });
    await openPanel();
    await submitQuestion('무엇을 복습할까?');

    const copyButton = getStudyCardCopyButtons()[0];
    if (!copyButton) throw new Error('study card copy button not found');

    await clickStudyCardCopy(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith([
      '# 근거 Q&A 복습 카드: 노트 제목',
      '',
      '원본 노트: /notes/n1',
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
    expect(JSON.parse(window.localStorage.getItem('ie:result-chat-study-cards:v1') ?? '[]')[0]).toMatchObject({
      title: '노트 제목',
      question: '무엇을 복습할까?',
      answer: '핵심 답변',
      sourceHref: '/notes/n1',
    });
    expect(document.body.textContent).toContain('복사+저장 완료');
  });

  it('shows a partial-success message when storage fails after the card is copied', async () => {
    vi.mocked(askResultChat).mockResolvedValueOnce({ answer: '저장 실패 답변' });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('storage unavailable');
    });

    await renderPanel();
    await openPanel();
    await submitQuestion('저장 실패 질문');

    const copyButton = getStudyCardCopyButtons()[0];
    if (!copyButton) throw new Error('study card copy button not found');
    await clickStudyCardCopy(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledOnce();
    expect(copyButton.parentElement?.textContent).toContain('복사 완료 · 저장 실패');
    expect(copyButton.parentElement?.textContent).not.toContain('복사+저장 완료');
  });

  it('shows that saving succeeded even when copying fails', async () => {
    vi.mocked(askResultChat).mockResolvedValueOnce({ answer: '복사 실패 답변' });
    vi.mocked(navigator.clipboard.writeText).mockRejectedValueOnce(new Error('permission denied'));
    Object.defineProperty(document, 'execCommand', {
      configurable: true,
      value: vi.fn().mockReturnValue(false),
    });

    await renderPanel();
    await openPanel();
    await submitQuestion('복사 실패 질문');

    const copyButton = getStudyCardCopyButtons()[0];
    if (!copyButton) throw new Error('study card copy button not found');
    await clickStudyCardCopy(copyButton);

    expect(copyButton.parentElement?.textContent).toContain('저장 완료 · 복사 실패');
    expect(copyButton.parentElement?.textContent).not.toContain('복사 완료 · 저장 실패');
    expect(copyButton.parentElement?.textContent).not.toContain('복사+저장 완료');
  });

  it('shows a failure state when study-card building fails', async () => {
    vi.mocked(askResultChat).mockResolvedValueOnce({ answer: '카드 빌드 실패 답변' });

    await renderPanel({ studyCardTitle: '\uD800' });
    await openPanel();
    await submitQuestion('카드 생성 실패 질문');

    const copyButton = getStudyCardCopyButtons()[0];
    if (!copyButton) throw new Error('study card copy button not found');
    await clickStudyCardCopy(copyButton);

    expect(copyButton.parentElement?.textContent).toContain('복사·저장 실패');
    expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
    expect(window.localStorage.getItem('ie:result-chat-study-cards:v1')).toBeNull();
  });

  it('keeps only the latest concurrent feedback and clears it after two seconds', async () => {
    vi.useFakeTimers();
    vi.mocked(askResultChat)
      .mockResolvedValueOnce({ answer: '첫 답변' })
      .mockResolvedValueOnce({ answer: '둘째 답변' });

    await renderPanel();
    await openPanel();
    await submitQuestion('첫 질문');
    await submitQuestion('둘째 질문');

    let resolveFirstCopy: () => void = () => undefined;
    vi.mocked(navigator.clipboard.writeText)
      .mockImplementationOnce(() => new Promise<void>((resolve) => {
        resolveFirstCopy = resolve;
      }))
      .mockResolvedValueOnce(undefined);
    vi.spyOn(Storage.prototype, 'setItem')
      .mockImplementationOnce(() => undefined)
      .mockImplementationOnce(() => {
        throw new Error('storage unavailable');
      });

    const [firstCopyButton, secondCopyButton] = getStudyCardCopyButtons();
    if (!firstCopyButton || !secondCopyButton) throw new Error('study card copy buttons not found');

    await clickStudyCardCopy(firstCopyButton);
    await clickStudyCardCopy(secondCopyButton);
    expect(secondCopyButton.parentElement?.textContent).not.toContain('복사 완료 · 저장 실패');

    await act(async () => {
      resolveFirstCopy();
      for (let index = 0; index < 8; index += 1) await Promise.resolve();
    });

    expect(firstCopyButton.parentElement?.textContent).not.toContain('복사+저장 완료');
    expect(secondCopyButton.parentElement?.textContent).toContain('복사 완료 · 저장 실패');

    await act(async () => vi.advanceTimersByTime(1_999));
    expect(secondCopyButton.parentElement?.textContent).toContain('복사 완료 · 저장 실패');

    await act(async () => vi.advanceTimersByTime(1));
    expect(secondCopyButton.parentElement?.textContent).not.toContain('복사 완료 · 저장 실패');
  });
});
