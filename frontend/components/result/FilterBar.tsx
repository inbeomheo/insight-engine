'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useResultStore } from '@/stores/resultStore';
import { STYLE_OPTIONS } from '@/lib/constants';

export default function FilterBar() {
  // reports.length만 구독 (전체 배열 구독 방지)
  const hasReports = useResultStore((s) => s.reports.length > 0);
  const searchQuery = useResultStore((s) => s.searchQuery);
  const styleFilter = useResultStore((s) => s.styleFilter);
  const setSearchQuery = useResultStore((s) => s.setSearchQuery);
  const setStyleFilter = useResultStore((s) => s.setStyleFilter);

  // 검색 입력 디바운스 (300ms) — 매 키 입력마다 필터링 방지
  const [localQuery, setLocalQuery] = useState(searchQuery);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    setLocalQuery(searchQuery);
  }, [searchQuery]);

  const handleSearchChange = useCallback((value: string) => {
    setLocalQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchQuery(value);
    }, 300);
  }, [setSearchQuery]);

  if (!hasReports) return null;

  return (
    <div className="flex items-center gap-3 w-full mb-5">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={localQuery}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="결과 검색..."
          className="pl-9 h-10 text-sm"
        />
      </div>
      <Select value={styleFilter || 'all'} onValueChange={(v) => setStyleFilter(v === 'all' ? '' : v)}>
        <SelectTrigger className="h-10 text-sm w-36">
          <SelectValue placeholder="스타일" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all" className="text-sm">전체</SelectItem>
          {STYLE_OPTIONS.map((s) => (
            <SelectItem key={s.id} value={s.id} className="text-sm">
              {s.emoji} {s.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
