'use client';

import { useState, useRef, useCallback, type DragEvent, type ChangeEvent } from 'react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

/**
 * 드래그앤드롭 파일 영역 공용 컴포넌트
 * - 드래그 오버 시 스타일 변경
 * - 파일 크기 초과 시 toast.error
 */
interface DropZoneProps {
  onFiles: (files: File[]) => void;
  accept?: string;     // e.g. '.pdf,.docx'
  maxSizeMB?: number;  // 기본 10
  children?: React.ReactNode;
  className?: string;
  disabled?: boolean;
  testId?: string;
  inputTestId?: string;
  ariaLabel?: string;
  ariaDescribedBy?: string;
}

export default function DropZone({
  onFiles,
  accept,
  maxSizeMB = 10,
  children,
  className,
  disabled,
  testId,
  inputTestId,
  ariaLabel,
  ariaDescribedBy,
}: DropZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const maxBytes = maxSizeMB * 1024 * 1024;

  // 파일 크기 검증 후 콜백 호출
  const processFiles = useCallback(
    (fileList: FileList | File[]) => {
      const files = Array.from(fileList);
      const valid: File[] = [];
      for (const f of files) {
        if (f.size > maxBytes) {
          toast.error(`${f.name}: 파일 크기가 ${maxSizeMB}MB를 초과합니다.`);
        } else {
          valid.push(f);
        }
      }
      if (valid.length > 0) onFiles(valid);
    },
    [maxBytes, maxSizeMB, onFiles],
  );

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      processFiles(e.dataTransfer.files);
    },
    [disabled, processFiles],
  );

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) processFiles(files);
      // input 초기화 (같은 파일 재선택 가능)
      e.target.value = '';
    },
    [processFiles],
  );

  return (
    <div
      data-testid={testId}
      role="button"
      aria-label={ariaLabel}
      aria-describedby={ariaDescribedBy}
      tabIndex={0}
      className={cn(
        'flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 transition-colors',
        dragOver
          ? 'border-primary bg-primary/5'
          : 'border-border/60 hover:border-primary/40',
        disabled && 'pointer-events-none opacity-50',
        className,
      )}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
    >
      {children}
      <input
        ref={inputRef}
        data-testid={inputTestId}
        type="file"
        accept={accept}
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
      />
    </div>
  );
}
