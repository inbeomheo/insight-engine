'use client';

import { memo, useState, useEffect, useRef, useCallback } from 'react';
import { Minimize2, Maximize2, Languages, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface InlineEditorProps {
  containerRef: React.RefObject<HTMLElement | null>;
  onEdit: (selection: string, instruction: string) => Promise<string | null>;
}

const ACTIONS = [
  { icon: Minimize2, label: '축약', instruction: '더 짧고 간결하게 줄여주세요' },
  { icon: Maximize2, label: '확장', instruction: '더 상세하고 풍부하게 확장해주세요' },
  { icon: Wand2, label: '톤 변경', instruction: '더 전문적인 톤으로 바꿔주세요' },
  { icon: Languages, label: '영문 번역', instruction: 'Translate to English' },
];

export const InlineEditor = memo(function InlineEditor({ containerRef, onEdit }: InlineEditorProps) {
  const [show, setShow] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const [selectedText, setSelectedText] = useState('');
  const [loading, setLoading] = useState(false);
  const toolbarRef = useRef<HTMLDivElement>(null);

  const handleSelection = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {
      setShow(false);
      return;
    }

    // 컨테이너 내부 선택인지 확인
    if (!containerRef.current?.contains(sel.anchorNode)) {
      setShow(false);
      return;
    }

    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const containerRect = containerRef.current.getBoundingClientRect();

    setPos({
      top: rect.top - containerRect.top - 40,
      left: rect.left - containerRect.left + rect.width / 2,
    });
    setSelectedText(sel.toString().trim());
    setShow(true);
  }, [containerRef]);

  useEffect(() => {
    document.addEventListener('selectionchange', handleSelection);
    return () => document.removeEventListener('selectionchange', handleSelection);
  }, [handleSelection]);

  async function handleAction(instruction: string) {
    if (loading || !selectedText) return;
    setLoading(true);
    try {
      const result = await onEdit(selectedText, instruction);
      if (result) {
        toast.success('편집 완료');
      }
    } catch {
      toast.error('편집 실패');
    } finally {
      setLoading(false);
      setShow(false);
    }
  }

  if (!show) return null;

  return (
    <div
      ref={toolbarRef}
      className="absolute z-50 flex gap-1 p-1 rounded-lg bg-white dark:bg-zinc-800 shadow-lg border border-zinc-200 dark:border-zinc-700"
      style={{ top: pos.top, left: pos.left, transform: 'translateX(-50%)' }}
    >
      {ACTIONS.map((action) => (
        <Button
          key={action.label}
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={() => handleAction(action.instruction)}
          disabled={loading}
        >
          <action.icon className="h-3 w-3 mr-1" />
          {action.label}
        </Button>
      ))}
    </div>
  );
});

export default InlineEditor;
