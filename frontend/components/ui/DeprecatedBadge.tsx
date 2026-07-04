'use client';

import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useTranslation } from '@/hooks/useTranslation';
import { cn } from '@/lib/utils';

/**
 * 발행 계열 기능(학습 엔진 피벗으로 단계적 정리 대상)에 붙이는 지원 종료 예정 배지.
 * 시각적 강등 전용 — 기능 제거 없음.
 */
export function DeprecatedBadge({ className }: { className?: string }) {
  const { t } = useTranslation();
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          tabIndex={0}
          variant="outline"
          className={cn(
            'text-muted-foreground border-muted-foreground/40 text-[10px] px-1.5 py-0 cursor-default',
            className
          )}
        >
          {t('common.deprecated')}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>
        {t('common.deprecatedTooltip')}
      </TooltipContent>
    </Tooltip>
  );
}
