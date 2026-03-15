'use client';

import { memo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Loader2 } from 'lucide-react';

const LoadingSkeleton = memo(function LoadingSkeleton() {
  return (
    <Card className="overflow-hidden border-border/40 shadow-sm" aria-busy="true" aria-label="콘텐츠 생성 중">
      <div className="px-5 pt-5 pb-2">
        <div className="flex items-center gap-2.5 mb-4">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-4 w-12 rounded" />
        </div>
        <Skeleton className="h-6 w-3/4 mb-2.5 rounded" />
        <Skeleton className="h-4 w-1/2 rounded" />
      </div>
      <CardContent className="px-5 pb-5 pt-0">
        <div className="flex items-center gap-2.5 text-sm text-muted-foreground mb-4">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          <span className="font-medium">콘텐츠 생성 중...</span>
        </div>
        <div className="space-y-2.5">
          <Skeleton className="h-4 w-full rounded" />
          <Skeleton className="h-4 w-5/6 rounded" />
          <Skeleton className="h-4 w-4/6 rounded" />
          <Skeleton className="h-4 w-full rounded" />
          <Skeleton className="h-4 w-3/4 rounded" />
        </div>
      </CardContent>
    </Card>
  );
});

export default LoadingSkeleton;
