'use client';

import { useCallback } from 'react';
import { useKnowledge } from '@/hooks/useKnowledge';
import DropZone from '@/components/ui/DropZone';

const ALLOWED_EXTENSIONS = '.txt,.md,.pdf';
const MAX_FILE_SIZE_MB = 10;

export default function KnowledgeManager() {
  const { documents, isLoading, upload, isUploading, remove, isDeleting } = useKnowledge();

  const handleFiles = useCallback(
    (files: File[]) => {
      const file = files[0];
      if (file) upload(file);
    },
    [upload],
  );

  return (
    <div>
      <label className="text-sm font-medium text-muted-foreground mb-2 block">
        지식 베이스
      </label>

      {/* 드래그 영역 — DropZone 공용 컴포넌트 사용 */}
      <DropZone
        onFiles={handleFiles}
        accept={ALLOWED_EXTENSIONS}
        maxSizeMB={MAX_FILE_SIZE_MB}
        disabled={isUploading}
        className="p-4 text-center"
      >
        <p className="text-sm text-muted-foreground">
          {isUploading ? '업로드 중...' : '파일을 드래그하거나 클릭하여 업로드'}
        </p>
        <p className="text-xs text-muted-foreground/70 mt-1">
          .txt, .md, .pdf (최대 {MAX_FILE_SIZE_MB}MB)
        </p>
      </DropZone>

      {/* 문서 목록 */}
      {isLoading ? (
        <p className="text-xs text-muted-foreground mt-2">불러오는 중...</p>
      ) : documents.length > 0 ? (
        <ul className="mt-3 space-y-1.5">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className="flex items-center justify-between text-sm bg-muted/50 rounded-lg px-3 py-2"
            >
              <div className="min-w-0 flex-1">
                <span className="font-medium truncate block">{doc.filename}</span>
                <span className="text-xs text-muted-foreground">
                  {doc.chunk_count}개 청크
                </span>
              </div>
              <button
                onClick={() => remove(doc.id)}
                disabled={isDeleting}
                aria-label={`${doc.filename} 문서 삭제`}
                className="ml-2 text-xs text-red-500 hover:text-red-600 disabled:opacity-50 shrink-0"
              >
                삭제
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-muted-foreground mt-2">
          업로드된 문서가 없습니다. 참고 자료를 추가하면 콘텐츠 생성 시 자동으로 참조됩니다.
        </p>
      )}
    </div>
  );
}
