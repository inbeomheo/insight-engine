'use client';

import { useState, useCallback } from 'react';
import { FileUp, X, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import DropZone from '@/components/ui/DropZone';

const ACCEPTED_TYPES = '.pdf,.docx';
const ACCEPTED_MIME = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_SIZE_MB = 10;

interface FileUploadProps {
  file: File | null;
  onFileSelect: (file: File | null) => void;
  disabled?: boolean;
}

export default function FileUpload({ file, onFileSelect, disabled }: FileUploadProps) {
  const [error, setError] = useState('');

  // MIME/확장자 + 빈 파일 검증 (크기 초과는 DropZone이 처리)
  const handleFiles = useCallback(
    (files: File[]) => {
      const f = files[0];
      if (!f) return;
      if (!ACCEPTED_MIME.includes(f.type) && !f.name.match(/\.(pdf|docx)$/i)) {
        setError('PDF 또는 DOCX 파일만 업로드 가능합니다.');
        setTimeout(() => setError(''), 3000);
        return;
      }
      if (f.size === 0) {
        setError('빈 파일입니다.');
        setTimeout(() => setError(''), 3000);
        return;
      }
      setError('');
      onFileSelect(f);
    },
    [onFileSelect],
  );

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
      <DropZone
        onFiles={handleFiles}
        accept={ACCEPTED_TYPES}
        maxSizeMB={MAX_SIZE_MB}
        disabled={disabled}
      >
        <FileUp className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          PDF, DOCX 파일을 드래그하거나 클릭하여 업로드
        </p>
        <p className="text-xs text-muted-foreground/60">최대 {MAX_SIZE_MB}MB</p>
      </DropZone>
      {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
    </div>
  );
}
