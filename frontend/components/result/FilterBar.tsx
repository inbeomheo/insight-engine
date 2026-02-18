'use client';

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
  const { searchQuery, styleFilter, setSearchQuery, setStyleFilter, reports } =
    useResultStore();

  if (reports.length === 0) return null;

  return (
    <div className="flex items-center gap-3 w-full mb-5">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
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
