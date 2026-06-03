'use client';

import { useState, useEffect, memo } from 'react';
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
import { useDebouncedValue } from '@/hooks/useDebouncedValue';

const FilterBar = memo(function FilterBar() {
  // reports.length만 구독 (전체 배열 구독 방지)
  const hasReports = useResultStore((s) => s.reports.length > 0);
  const searchQuery = useResultStore((s) => s.searchQuery);
  const styleFilter = useResultStore((s) => s.styleFilter);
  const setSearchQuery = useResultStore((s) => s.setSearchQuery);
  const setStyleFilter = useResultStore((s) => s.setStyleFilter);

  // 검색 입력 디바운스 (300ms) — 매 키 입력마다 필터링 방지
  const [localQuery, setLocalQuery] = useState(searchQuery);
  const debouncedQuery = useDebouncedValue(localQuery, 300);

  // 외부에서 searchQuery가 변경되면 로컬 상태 동기화
  useEffect(() => {
    setLocalQuery(searchQuery);
  }, [searchQuery]);

  // 디바운스된 값이 변경되면 스토어에 반영
  useEffect(() => {
    setSearchQuery(debouncedQuery);
  }, [debouncedQuery, setSearchQuery]);

  if (!hasReports) return null;

  return (
    <div className="flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <Input
          data-testid="result-filter-search"
          type="search"
          value={localQuery}
          onChange={(e) => setLocalQuery(e.target.value)}
          placeholder="결과 검색..."
          className="pl-9 h-10 text-sm"
          aria-label="결과 검색"
          aria-describedby="result-filter-search-help"
        />
        <p id="result-filter-search-help" data-testid="result-filter-search-help" className="sr-only">
          제목과 본문에서 결과를 검색합니다.
        </p>
      </div>
      <Select value={styleFilter || 'all'} onValueChange={(v) => setStyleFilter(v === 'all' ? '' : v)}>
        <SelectTrigger data-testid="result-filter-style-trigger" aria-label="스타일 필터" aria-describedby="result-filter-style-help" className="h-10 text-sm w-36">
          <SelectValue placeholder="스타일" />
        </SelectTrigger>
        <p id="result-filter-style-help" data-testid="result-filter-style-help" className="sr-only">
          산출물 스타일로 결과를 좁힙니다.
        </p>
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
});

export default FilterBar;
