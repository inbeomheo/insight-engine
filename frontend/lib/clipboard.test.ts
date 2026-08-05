import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { copyTextToClipboard } from './clipboard';

let clipboardDescriptor: PropertyDescriptor | undefined;
let execCommandDescriptor: PropertyDescriptor | undefined;

function setClipboard(writeText?: (text: string) => Promise<void>) {
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: writeText ? { writeText } : undefined,
  });
}

function setExecCommand(execCommand: (command: string) => boolean) {
  Object.defineProperty(document, 'execCommand', {
    configurable: true,
    value: execCommand,
  });
}

function restoreProperty(
  target: object,
  property: PropertyKey,
  descriptor: PropertyDescriptor | undefined,
) {
  if (descriptor) {
    Object.defineProperty(target, property, descriptor);
    return;
  }
  Reflect.deleteProperty(target, property);
}

describe('copyTextToClipboard', () => {
  beforeEach(() => {
    clipboardDescriptor = Object.getOwnPropertyDescriptor(navigator, 'clipboard');
    execCommandDescriptor = Object.getOwnPropertyDescriptor(document, 'execCommand');
  });

  afterEach(() => {
    restoreProperty(navigator, 'clipboard', clipboardDescriptor);
    restoreProperty(document, 'execCommand', execCommandDescriptor);
    document.querySelectorAll('textarea').forEach((textarea) => textarea.remove());
    vi.restoreAllMocks();
  });

  it('네이티브 Clipboard API 성공 결과를 반환한다', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const execCommand = vi.fn().mockReturnValue(true);
    setClipboard(writeText);
    setExecCommand(execCommand);

    await expect(copyTextToClipboard('복사할 내용')).resolves.toEqual({
      copied: true,
      isCurrent: true,
    });

    expect(writeText).toHaveBeenCalledWith('복사할 내용');
    expect(execCommand).not.toHaveBeenCalled();
    expect(document.querySelector('textarea')).toBeNull();
  });

  it('대기 중인 쓰기가 없으면 네이티브 복사를 즉시 시작한다', async () => {
    let resolveWrite: () => void = () => undefined;
    const writeText = vi.fn(() => new Promise<void>((resolve) => {
      resolveWrite = resolve;
    }));
    setClipboard(writeText);

    const copyPromise = copyTextToClipboard('즉시 복사');

    expect(writeText).toHaveBeenCalledWith('즉시 복사');
    resolveWrite();
    await expect(copyPromise).resolves.toEqual({ copied: true, isCurrent: true });
  });

  it('네이티브 복사가 실패하면 숨김 textarea 폴백으로 복사한다', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'));
    const execCommand = vi.fn(() => {
      const textarea = document.querySelector('textarea');
      expect(textarea).toBeInstanceOf(HTMLTextAreaElement);
      expect((textarea as HTMLTextAreaElement).value).toBe('폴백 내용');
      expect((textarea as HTMLTextAreaElement).readOnly).toBe(true);
      expect((textarea as HTMLTextAreaElement).style.position).toBe('fixed');
      expect((textarea as HTMLTextAreaElement).style.left).toBe('-9999px');
      return true;
    });
    setClipboard(writeText);
    setExecCommand(execCommand);

    await expect(copyTextToClipboard('폴백 내용')).resolves.toEqual({
      copied: true,
      isCurrent: true,
    });

    expect(execCommand).toHaveBeenCalledWith('copy');
    expect(document.querySelector('textarea')).toBeNull();
  });

  it('네이티브 API가 없어도 폴백 성공 여부를 반환한다', async () => {
    const execCommand = vi.fn().mockReturnValue(true);
    setClipboard();
    setExecCommand(execCommand);

    await expect(copyTextToClipboard('폴백 내용')).resolves.toEqual({
      copied: true,
      isCurrent: true,
    });

    expect(execCommand).toHaveBeenCalledWith('copy');
    expect(document.querySelector('textarea')).toBeNull();
  });

  it('오래된 네이티브 실패 요청은 textarea 폴백을 건너뛴다', async () => {
    let rejectWrite: (error: Error) => void = () => undefined;
    let current = true;
    const writeText = vi.fn(() => new Promise<void>((_resolve, reject) => {
      rejectWrite = reject;
    }));
    const execCommand = vi.fn().mockReturnValue(true);
    setClipboard(writeText);
    setExecCommand(execCommand);

    const copyPromise = copyTextToClipboard('오래된 내용', {
      shouldContinue: () => current,
    });
    current = false;
    rejectWrite(new Error('denied'));

    await expect(copyPromise).resolves.toEqual({ copied: false, isCurrent: false });
    expect(execCommand).not.toHaveBeenCalled();
  });

  it('오래된 비동기 텍스트는 네이티브 복사를 시작하지 않는다', async () => {
    let resolveText: (text: string) => void = () => undefined;
    let current = true;
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);

    const copyPromise = copyTextToClipboard(
      () => new Promise<string>((resolve) => {
        resolveText = resolve;
      }),
      { shouldContinue: () => current },
    );
    current = false;
    resolveText('오래된 내용');

    await expect(copyPromise).resolves.toEqual({ copied: false, isCurrent: false });
    expect(writeText).not.toHaveBeenCalled();
  });

  it('textarea 폴백 복사 후 기존 포커스를 복원한다', async () => {
    const focusTarget = document.createElement('button');
    document.body.appendChild(focusTarget);
    focusTarget.focus();
    setClipboard();
    setExecCommand(vi.fn().mockReturnValue(true));

    await expect(copyTextToClipboard('포커스 복원')).resolves.toEqual({
      copied: true,
      isCurrent: true,
    });

    expect(document.activeElement).toBe(focusTarget);
    expect(document.querySelector('textarea')).toBeNull();
    focusTarget.remove();
  });

  it('기존 포커스 복원에 실패해도 복사 성공 결과를 유지한다', async () => {
    const focusTarget = document.createElement('button');
    document.body.appendChild(focusTarget);
    focusTarget.focus();
    const focusSpy = vi.spyOn(focusTarget, 'focus').mockImplementation(() => {
      throw new Error('focus restore failed');
    });
    setClipboard();
    setExecCommand(vi.fn().mockReturnValue(true));

    await expect(copyTextToClipboard('복원 실패')).resolves.toEqual({
      copied: true,
      isCurrent: true,
    });

    expect(focusSpy).toHaveBeenCalledOnce();
    expect(document.querySelector('textarea')).toBeNull();
    focusTarget.remove();
  });

  it('폴백 복사 실패 결과를 반환하고 textarea를 정리한다', async () => {
    setClipboard();
    setExecCommand(vi.fn().mockReturnValue(false));

    await expect(copyTextToClipboard('실패할 내용')).resolves.toEqual({
      copied: false,
      isCurrent: true,
    });

    expect(document.querySelector('textarea')).toBeNull();
  });

  it('폴백 복사 중 예외가 발생해도 실패 결과를 반환하고 textarea를 정리한다', async () => {
    setClipboard();
    setExecCommand(vi.fn(() => {
      throw new Error('copy failed');
    }));

    await expect(copyTextToClipboard('예외 내용')).resolves.toEqual({
      copied: false,
      isCurrent: true,
    });

    expect(document.querySelector('textarea')).toBeNull();
  });
});
