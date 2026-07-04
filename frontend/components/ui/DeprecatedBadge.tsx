'use client';

import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

/**
 * 발행 계열 기능(학습 엔진 피벗으로 단계적 정리 대상)에 붙이는 지원 종료 예정 배지.
 * 시각적 강등 전용 — 기능 제거 없음.
 */
export function DeprecatedBadge() {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className="text-muted-foreground border-muted-foreground/40 text-[10px] px-1.5 py-0 cursor-default"
        >
          지원 종료 예정
        </Badge>
      </TooltipTrigger>
      <TooltipContent>
        학습 엔진 전환으로 발행 기능은 단계적으로 정리됩니다
      </TooltipContent>
    </Tooltip>
  );
}

export default DeprecatedBadge;
