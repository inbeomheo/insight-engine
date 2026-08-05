export type ClipboardTextSource = string | (() => string | Promise<string>);
export type ClipboardItemsSource = ClipboardItem[] | (() => ClipboardItem[] | Promise<ClipboardItem[]>);

export interface ClipboardCopyOptions {
  shouldContinue?: () => boolean;
}

export interface ClipboardOperationResult {
  copied: boolean;
  isCurrent: boolean;
}

let latestClipboardRequestId = 0;
let clipboardWriteTail: Promise<void> | null = null;

function canContinue(shouldContinue?: () => boolean): boolean {
  try {
    return shouldContinue?.() ?? true;
  } catch {
    return false;
  }
}

function beginClipboardRequest(shouldContinue?: () => boolean): () => boolean {
  const requestId = ++latestClipboardRequestId;
  return () => (
    requestId === latestClipboardRequestId && canContinue(shouldContinue)
  );
}

function enqueueClipboardWrite(operation: () => Promise<boolean>): Promise<boolean> {
  let result: Promise<boolean>;
  try {
    result = clipboardWriteTail ? clipboardWriteTail.then(operation) : operation();
  } catch (error) {
    result = Promise.reject(error);
  }

  const tail = result.then(
    () => undefined,
    () => undefined,
  );
  clipboardWriteTail = tail;
  void tail.then(() => {
    if (clipboardWriteTail === tail) clipboardWriteTail = null;
  });
  return result;
}

function copyWithTextarea(text: string): boolean {
  let textarea: HTMLTextAreaElement | null = null;
  let previousActiveElement: HTMLElement | null = null;

  try {
    if (
      typeof document === 'undefined'
      || !document.body
      || typeof document.execCommand !== 'function'
    ) {
      return false;
    }

    if (document.activeElement instanceof HTMLElement) {
      previousActiveElement = document.activeElement;
    }

    textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.setAttribute('aria-hidden', 'true');
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    textarea.style.top = '0';
    textarea.style.opacity = '0';
    textarea.style.pointerEvents = 'none';

    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    return document.execCommand('copy');
  } catch {
    return false;
  } finally {
    if (textarea?.parentNode) {
      try {
        textarea.parentNode.removeChild(textarea);
      } catch {
        // 정리 실패가 복사 결과를 덮어쓰지 않도록 한다.
      }
    }

    if (previousActiveElement) {
      try {
        previousActiveElement.focus({ preventScroll: true });
      } catch {
        // 포커스 복원 실패가 복사 결과를 덮어쓰지 않도록 한다.
      }
    }
  }
}

async function copyTextImmediately(
  text: string,
  isCurrent: () => boolean,
): Promise<boolean> {
  try {
    const clipboard = typeof navigator === 'undefined'
      ? undefined
      : navigator.clipboard;
    if (typeof clipboard?.writeText === 'function') {
      await clipboard.writeText(text);
      return true;
    }
  } catch {
    // 권한 거부 등 네이티브 복사 실패 시 레거시 폴백을 시도한다.
  }

  if (!isCurrent()) return false;
  return copyWithTextarea(text);
}

export async function copyTextToClipboard(
  source: ClipboardTextSource,
  { shouldContinue }: ClipboardCopyOptions = {},
): Promise<ClipboardOperationResult> {
  const isCurrent = beginClipboardRequest(shouldContinue);
  try {
    if (!isCurrent()) return { copied: false, isCurrent: false };
    const text = typeof source === 'function' ? await source() : source;
    if (!isCurrent()) return { copied: false, isCurrent: false };
    const copied = await enqueueClipboardWrite(async () => {
      if (!isCurrent()) return false;
      return copyTextImmediately(text, isCurrent);
    });
    return { copied, isCurrent: isCurrent() };
  } catch {
    return { copied: false, isCurrent: isCurrent() };
  }
}

export async function copyItemsToClipboard(
  source: ClipboardItemsSource,
  { shouldContinue }: ClipboardCopyOptions = {},
): Promise<ClipboardOperationResult> {
  const isCurrent = beginClipboardRequest(shouldContinue);
  try {
    if (!isCurrent()) return { copied: false, isCurrent: false };
    const items = typeof source === 'function' ? await source() : source;
    if (!isCurrent()) return { copied: false, isCurrent: false };
    const copied = await enqueueClipboardWrite(async () => {
      if (!isCurrent()) return false;
      try {
        const clipboard = typeof navigator === 'undefined'
          ? undefined
          : navigator.clipboard;
        if (typeof clipboard?.write !== 'function') return false;
        await clipboard.write(items);
        return true;
      } catch {
        return false;
      }
    });
    return { copied, isCurrent: isCurrent() };
  } catch {
    return { copied: false, isCurrent: isCurrent() };
  }
}
