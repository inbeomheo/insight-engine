'use client';

import { useState, useEffect } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface UsageAlertProps {
  used: number;
  total: number;
  thresholds?: number[];
}

/** 사용량 임계치 도달 시 경고 배너 (F4-09) */
export default function UsageAlert({ used, total, thresholds = [80, 100] }: UsageAlertProps) {
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  if (total <= 0) return null;

  const percentage = (used / total) * 100;

  // 아직 dismiss 안 한 가장 높은 임계치 찾기
  const activeThreshold = [...thresholds]
    .sort((a, b) => b - a)
    .find((t) => percentage >= t && !dismissed.has(t));

  if (!activeThreshold) return null;

  const isMax = activeThreshold >= 100;
  const bgColor = isMax ? 'bg-red-500/10 border-red-500/30' : 'bg-amber-500/10 border-amber-500/30';
  const textColor = isMax ? 'text-red-400' : 'text-amber-400';

  return (
    <div className={`flex items-center gap-3 rounded-lg border px-4 py-3 ${bgColor}`}>
      <AlertTriangle className={`h-5 w-5 shrink-0 ${textColor}`} />
      <p className={`flex-1 text-sm ${textColor}`}>
        사용량이 {activeThreshold}%에 도달했습니다. ({used}/{total})
        {isMax && ' 추가 크레딧을 구매하거나 플랜을 업그레이드하세요.'}
      </p>
      <button
        onClick={() => setDismissed((prev) => new Set(prev).add(activeThreshold))}
        className="shrink-0 rounded p-1 hover:bg-white/10"
        aria-label="사용량 경고 닫기"
      >
        <X className="h-4 w-4 text-gray-400" />
      </button>
    </div>
  );
}
