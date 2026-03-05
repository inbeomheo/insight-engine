'use client';

import { useState, useRef, type ChangeEvent } from 'react';
import { Bookmark, FileUp, Loader2, X, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface BookmarkItem {
  url: string;
  title: string;
  selected: boolean;
}

interface BookmarkImportProps {
  /** 선택된 URL 목록을 부모에 전달 */
  onUrlsSelected: (urls: string[]) => void;
  disabled?: boolean;
}

export default function BookmarkImport({ onUrlsSelected, disabled }: BookmarkImportProps) {
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [parsing, setParsing] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFileSelect(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.html') && !file.name.toLowerCase().endsWith('.htm')) {
      toast.error('HTML 파일만 업로드 가능합니다.');
      return;
    }

    setParsing(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const res = await fetch('/api/bookmarks/parse', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || '파싱 실패');

      const items: BookmarkItem[] = (data.bookmarks || []).map(
        (b: { url: string; title: string }) => ({
          ...b,
          selected: true,
        }),
      );
      setBookmarks(items);
      toast.success(`${items.length}개의 북마크를 불러왔습니다.`);
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : '북마크 파싱에 실패했습니다.');
    } finally {
      setParsing(false);
    }
  }

  function toggleItem(index: number) {
    setBookmarks((prev) =>
      prev.map((b, i) => (i === index ? { ...b, selected: !b.selected } : b)),
    );
  }

  function toggleAll() {
    const allSelected = bookmarks.every((b) => b.selected);
    setBookmarks((prev) => prev.map((b) => ({ ...b, selected: !allSelected })));
  }

  function handleConfirm() {
    const selected = bookmarks.filter((b) => b.selected).map((b) => b.url);
    if (selected.length === 0) {
      toast.error('URL을 선택해주세요.');
      return;
    }
    onUrlsSelected(selected);
    setBookmarks([]);
  }

  function handleCancel() {
    setBookmarks([]);
  }

  // 북마크 목록이 있으면 선택 UI 표시
  if (bookmarks.length > 0) {
    const selectedCount = bookmarks.filter((b) => b.selected).length;
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium flex items-center gap-1.5">
            <Bookmark className="h-4 w-4" />
            북마크 ({selectedCount}/{bookmarks.length}개 선택)
          </h4>
          <div className="flex gap-1.5">
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={toggleAll}>
              {bookmarks.every((b) => b.selected) ? '전체 해제' : '전체 선택'}
            </Button>
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={handleCancel}>
              <X className="h-3 w-3 mr-1" />
              취소
            </Button>
            <Button size="sm" className="h-7 text-xs" onClick={handleConfirm} disabled={selectedCount === 0}>
              <Check className="h-3 w-3 mr-1" />
              추가
            </Button>
          </div>
        </div>
        <ul className="max-h-48 overflow-y-auto space-y-1 rounded-md border p-2">
          {bookmarks.map((b, i) => (
            <li
              key={i}
              className="flex items-center gap-2 rounded px-2 py-1 hover:bg-muted/50 cursor-pointer text-sm"
              onClick={() => toggleItem(i)}
            >
              <input
                type="checkbox"
                checked={b.selected}
                readOnly
                className="rounded border-border"
              />
              <span className="truncate flex-1">{b.title}</span>
              <span className="text-xs text-muted-foreground truncate max-w-[200px]">{b.url}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  // 파일 선택 버튼
  return (
    <div>
      <Button
        variant="outline"
        size="sm"
        className="h-8 text-xs"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || parsing}
      >
        {parsing ? (
          <Loader2 className="h-3 w-3 animate-spin mr-1.5" />
        ) : (
          <FileUp className="h-3 w-3 mr-1.5" />
        )}
        북마크 가져오기
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept=".html,.htm"
        className="hidden"
        onChange={handleFileSelect}
        disabled={disabled || parsing}
      />
    </div>
  );
}
