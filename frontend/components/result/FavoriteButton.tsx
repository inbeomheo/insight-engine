'use client';

import { useCallback } from 'react';
import { Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useResultStore } from '@/stores/resultStore';

interface FavoriteButtonProps {
  reportId: string;
  /** 현재 즐겨찾기 여부 (Report에 favorite 필드가 있다고 가정) */
  isFavorite?: boolean;
}

/** 즐겨찾기 별표 버튼 (F5-12) */
export default function FavoriteButton({ reportId, isFavorite = false }: FavoriteButtonProps) {
  const updateReport = useResultStore((s) => s.updateReport);

  const toggle = useCallback(() => {
    updateReport(reportId, { favorite: !isFavorite } as never);
  }, [reportId, isFavorite, updateReport]);

  return (
    <Button
      variant="ghost"
      size="icon"
      className={`h-7 w-7 transition-colors ${
        isFavorite
          ? 'text-amber-500 hover:text-amber-600'
          : 'text-muted-foreground/30 hover:text-amber-400'
      }`}
      onClick={toggle}
      aria-label={isFavorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}
    >
      <Star className={`h-4 w-4 ${isFavorite ? 'fill-current' : ''}`} />
    </Button>
  );
}
