'use client';

import { useState, useRef, type DragEvent, type ChangeEvent } from 'react';
import { FileUp, X, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';

const ACCEPTED_TYPES = '.pdf,.docx';
const ACCEPTED_MIME = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_SIZE_MB = 10;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

interface FileUploadProps {
  file: File | null;
  onFileSelect: (file: File | null) => void;
  disabled?: boolean;
}

export default function FileUpload({ file, onFileSelect, disabled }: FileUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  function validate(f: File): string | null {
    if (!ACCEPTED_MIME.includes(f.type) && !f.name.match(/\.(pdf|docx)$/i)) {
      return 'PDF 또는 DOCX 파일만 업로드 가능합니다.';
    }
    if (f.size > MAX_SIZE_BYTES) {
      return `파일 크기가 ${MAX_SIZE_MB}MB를 초과합니다.`;
    }
    if (f.size === 0) {
      return '빈 파일입니다.';
    }
    return null;
  }

  function handleFile(f: File) {
    const err = validate(f);
    if (err) {
      setError(err);
      setTimeout(() => setError(''), 3000);
      return;
    }
    setError('');
    onFileSelect(f);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
    // input 초기화 (같은 파일 재선택 가능하게)
    e.target.value = '';
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
  }

  if (file) {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-muted/30 px-4 py-3">
        <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{file.name}</p>
          <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={() => onFileSelect(null)}
          disabled={disabled}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        className={`
          flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6
          transition-colors
          ${dragOver ? 'border-primary bg-primary/5' : 'border-border/60 hover:border-primary/40'}
          ${disabled ? 'pointer-events-none opacity-50' : ''}
        `}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click(); }}
      >
        <FileUp className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          PDF, DOCX 파일을 드래그하거나 클릭하여 업로드
        </p>
        <p className="text-xs text-muted-foreground/60">최대 {MAX_SIZE_MB}MB</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        className="hidden"
        onChange={handleChange}
        disabled={disabled}
      />
      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </div>
  );
}
