'use client';

import { useEffect, useCallback } from 'react';

const URL_PATTERN = /^https?:\/\/.+/i;

interface ClipboardPasteProps {
  /** URL이 붙여넣기되면 호출 */
  onPasteUrl: (url: string) => void;
  /** 일반 텍스트가 붙여넣기되면 호출 */
  onPasteText: (text: string) => void;
  /** 활성 상태 (false면 이벤트 무시) */
  enabled?: boolean;
}

/**
 * 전역 Ctrl+V / Cmd+V 이벤트를 감지하여
 * URL이면 onPasteUrl, 텍스트면 onPasteText로 라우팅합니다.
 * input/textarea에 포커스가 있으면 기본 동작을 방해하지 않습니다.
 */
export default function ClipboardPaste({
  onPasteUrl,
  onPasteText,
  enabled = true,
}: ClipboardPasteProps) {
  const handlePaste = useCallback(
    (e: ClipboardEvent) => {
      if (!enabled) return;

      // input, textarea, contenteditable에 포커스가 있으면 기본 동작 유지
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      const text = e.clipboardData?.getData('text')?.trim();
      if (!text) return;

      const isUrl = URL_PATTERN.test(text);
      const isLongText = text.length >= 10;
      if (!isUrl && !isLongText) return;

      e.preventDefault();

      if (isUrl) {
        onPasteUrl(text);
      } else {
        onPasteText(text);
      }
    },
    [enabled, onPasteUrl, onPasteText],
  );

  useEffect(() => {
    document.addEventListener('paste', handlePaste);
    return () => document.removeEventListener('paste', handlePaste);
  }, [handlePaste]);

  // 렌더링 없는 이벤트 리스너 컴포넌트
  return null;
}
