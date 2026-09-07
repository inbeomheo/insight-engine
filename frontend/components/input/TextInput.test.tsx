import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setAuthSession, type AuthSession } from '@/lib/auth-session';
import TextInput from './TextInput';

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

const { extractAudioMock, extractDocumentMock } = vi.hoisted(() => ({
  extractAudioMock: vi.fn(),
  extractDocumentMock: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  extractAudio: extractAudioMock,
  extractDocument: extractDocumentMock,
}));

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

async function selectFile(file: File) {
  const input = document.querySelector<HTMLInputElement>('input[type="file"]')!;
  Object.defineProperty(input, 'files', {
    configurable: true,
    value: [file],
  });
  await act(async () => {
    input.dispatchEvent(new Event('change', { bubbles: true }));
    await Promise.resolve();
  });
}

describe('TextInput 파일 추출 계정 격리', () => {
  let container: HTMLDivElement;
  let root: Root | null;
  let onChange: ReturnType<typeof vi.fn<(text: string) => void>>;

  beforeEach(() => {
    setAuthSession(null);
    localStorage.clear();
    extractAudioMock.mockReset();
    extractDocumentMock.mockReset();
    onChange = vi.fn<(text: string) => void>();
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(async () => {
    if (root) await act(async () => root!.unmount());
    setAuthSession(null);
    container.remove();
    vi.clearAllMocks();
  });

  async function renderInput() {
    await act(async () => {
      root!.render(
        <TextInput
          value=""
          onChange={onChange}
          onGenerate={() => {}}
          isLoading={false}
        />,
      );
    });
  }

  it('현재 계정의 문서 추출 결과는 텍스트로 전달한다', async () => {
    setAuthSession(authSession('account-a'));
    extractDocumentMock.mockResolvedValue({ text: '추출된 문서', truncated: false, pages: 1 });
    await renderInput();

    await selectFile(new File(['pdf'], 'document.pdf', { type: 'application/pdf' }));
    await vi.waitFor(() => expect(onChange).toHaveBeenCalledWith('추출된 문서'));
  });

  it('A 파일 추출이 끝나기 전 B로 전환하면 늦은 결과를 전달하지 않고 새 입력을 재마운트한다', async () => {
    setAuthSession(authSession('account-a'));
    const pending = deferred<{ text: string; truncated: boolean; pages: number }>();
    extractDocumentMock.mockImplementationOnce(() => pending.promise);
    await renderInput();
    await selectFile(new File(['pdf'], 'account-a.pdf', { type: 'application/pdf' }));
    expect(document.querySelector<HTMLButtonElement>('button[aria-label="파일 불러오기"]')?.disabled)
      .toBe(true);

    await act(async () => setAuthSession(authSession('account-b')));
    expect(document.querySelector<HTMLButtonElement>('button[aria-label="파일 불러오기"]')?.disabled)
      .toBe(false);

    await act(async () => {
      pending.resolve({ text: 'A의 늦은 추출 결과', truncated: false, pages: 1 });
      await Promise.resolve();
    });
    expect(onChange).not.toHaveBeenCalled();
  });

  it('언마운트 후 완료된 파일 추출이 상위 onChange를 호출하지 않는다', async () => {
    setAuthSession(authSession('account-a'));
    const pending = deferred<{ text: string; truncated: boolean; pages: number }>();
    extractDocumentMock.mockImplementationOnce(() => pending.promise);
    await renderInput();
    await selectFile(new File(['pdf'], 'unmount.pdf', { type: 'application/pdf' }));

    await act(async () => root!.unmount());
    root = null;
    pending.resolve({ text: '언마운트 후 결과', truncated: false, pages: 1 });
    await Promise.resolve();

    expect(onChange).not.toHaveBeenCalled();
  });
});
