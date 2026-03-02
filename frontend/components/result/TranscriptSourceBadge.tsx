'use client';

import { memo } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

/** 자막 소스 타입별 설정 */
const SOURCE_CONFIG: Record<
  string,
  { label: string; className: string; description: string }
> = {
  youtube_api: {
    label: '공식 자막',
    className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
    description: 'YouTube 공식 자막 API',
  },
  api: {
    label: '공식 자막',
    className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
    description: 'YouTube 공식 자막 API',
  },
  watch_page: {
    label: '웹 추출',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    description: 'YouTube 페이지에서 직접 추출',
  },
  watch: {
    label: '웹 추출',
    className: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
    description: 'YouTube 페이지에서 직접 추출',
  },
  supadata: {
    label: '외부 API',
    className: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    description: 'Supadata 외부 API 사용',
  },
  whisper: {
    label: '음성 인식',
    className: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
    description: 'Whisper 로컬 음성 인식',
  },
  cache: {
    label: '캐시',
    className: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
    description: '캐시된 자막 데이터',
  },
};

interface TranscriptSourceBadgeProps {
  /** 자막 소스 유형 (api, watch, supadata, whisper 등) */
  source: string;
  /** 품질 점수 (0.0 ~ 1.0) */
  qualityScore?: number;
  /** 자동 생성 자막 여부 */
  isAuto?: boolean;
  /** 추가 CSS 클래스 */
  className?: string;
}

export const TranscriptSourceBadge = memo(function TranscriptSourceBadge({
  source,
  qualityScore,
  isAuto,
  className,
}: TranscriptSourceBadgeProps) {
  const config = SOURCE_CONFIG[source] || {
    label: source,
    className: 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300',
    description: source,
  };

  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <Badge
        variant="outline"
        className={cn(
          'border-transparent text-[10px] px-1.5 py-0 h-5 font-medium',
          config.className
        )}
        title={config.description}
      >
        {config.label}
      </Badge>

      {/* 품질 바 */}
      {qualityScore != null && (
        <span
          className="inline-flex items-center gap-1 text-[10px] text-zinc-500 dark:text-zinc-400"
          title={`자막 품질: ${Math.round(qualityScore * 100)}%`}
        >
          <span className="relative w-8 h-1.5 rounded-full bg-zinc-200 dark:bg-zinc-700 overflow-hidden">
            <span
              className={cn(
                'absolute inset-y-0 left-0 rounded-full transition-all',
                qualityScore >= 0.8
                  ? 'bg-emerald-500'
                  : qualityScore >= 0.6
                    ? 'bg-amber-500'
                    : 'bg-red-500'
              )}
              style={{ width: `${qualityScore * 100}%` }}
            />
          </span>
          <span>{Math.round(qualityScore * 100)}%</span>
        </span>
      )}

      {/* 자동 생성 표시 */}
      {isAuto && (
        <span className="text-[10px] text-zinc-400 dark:text-zinc-500">
          (자동)
        </span>
      )}
    </span>
  );
});

export default TranscriptSourceBadge;
