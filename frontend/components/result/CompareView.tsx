'use client';

/**
 * CompareView — 콘텐츠 비교 뷰 (F8-21)
 *
 * 두 콘텐츠를 나란히 표시하고 차이점을 하이라이트합니다.
 * 간단한 줄 단위 diff를 수행합니다.
 */

import React, { useMemo } from 'react';
import { X } from 'lucide-react';

export interface CompareItem {
  id: string;
  title: string;
  content: string;
  style?: string;
  created_at?: string;
}

interface Props {
  left: CompareItem;
  right: CompareItem;
  onClose?: () => void;
}

type DiffLine = { text: string; type: 'same' | 'added' | 'removed' };

function computeDiff(a: string, b: string): { left: DiffLine[]; right: DiffLine[] } {
  const linesA = a.split('\n');
  const linesB = b.split('\n');
  const m = linesA.length;
  const n = linesB.length;

  // LCS (Longest Common Subsequence) 테이블 구축
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
  for (let i = 1; i <= m; i++)
    for (let j = 1; j <= n; j++)
      dp[i][j] = linesA[i - 1] === linesB[j - 1] ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1]);

  // 역추적으로 diff 생성
  const left: DiffLine[] = [];
  const right: DiffLine[] = [];
  let i = m, j = n;
  const stack: Array<{ left: DiffLine; right: DiffLine }> = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && linesA[i - 1] === linesB[j - 1]) {
      stack.push({
        left: { text: linesA[i - 1], type: 'same' },
        right: { text: linesB[j - 1], type: 'same' },
      });
      i--; j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      stack.push({
        left: { text: '', type: 'same' },
        right: { text: linesB[j - 1], type: 'added' },
      });
      j--;
    } else {
      stack.push({
        left: { text: linesA[i - 1], type: 'removed' },
        right: { text: '', type: 'same' },
      });
      i--;
    }
  }

  for (let k = stack.length - 1; k >= 0; k--) {
    left.push(stack[k].left);
    right.push(stack[k].right);
  }

  return { left, right };
}

function lineClass(type: DiffLine['type']): string {
  switch (type) {
    case 'added':   return 'bg-green-50 dark:bg-green-900/20 border-l-2 border-green-400';
    case 'removed': return 'bg-red-50 dark:bg-red-900/20 border-l-2 border-red-400';
    default:        return '';
  }
}

export default function CompareView({ left, right, onClose }: Props) {
  const diff = useMemo(() => computeDiff(left.content, right.content), [left.content, right.content]);

  const changedCount = diff.left.filter((l) => l.type !== 'same').length;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-slate-900 rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-700">
      {/* 헤더 */}
      <div className="flex items-center px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
        <div className="flex-1 text-sm font-semibold text-slate-700 dark:text-slate-200">
          콘텐츠 비교 ({changedCount}줄 변경)
        </div>
        {onClose && (
          <button
            onClick={onClose}
            aria-label="비교 뷰 닫기"
            className="p-1 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* 제목 영역 */}
      <div className="grid grid-cols-2 border-b border-slate-200 dark:border-slate-700">
        {[left, right].map((item, idx) => (
          <div
            key={item.id}
            className={`px-4 py-3 ${idx === 0 ? 'border-r border-slate-200 dark:border-slate-700' : ''}`}
          >
            <p className="text-xs text-slate-400 uppercase tracking-wide">
              {idx === 0 ? '기존' : '변경'}
            </p>
            <p className="font-semibold text-slate-800 dark:text-slate-100 line-clamp-1">
              {item.title}
            </p>
            {item.style && (
              <span className="text-xs text-slate-400">{item.style}</span>
            )}
          </div>
        ))}
      </div>

      {/* 본문 비교 */}
      <div className="grid grid-cols-2 flex-1 overflow-auto">
        {/* 왼쪽 */}
        <div className="border-r border-slate-200 dark:border-slate-700 overflow-auto">
          {diff.left.map((line, i) => (
            <div
              key={i}
              className={`flex gap-2 px-3 py-0.5 font-mono text-xs ${lineClass(line.type)}`}
            >
              <span className="text-slate-300 select-none w-6 text-right shrink-0">{i + 1}</span>
              <span className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap break-all">
                {line.text || '\u00A0'}
              </span>
            </div>
          ))}
        </div>

        {/* 오른쪽 */}
        <div className="overflow-auto">
          {diff.right.map((line, i) => (
            <div
              key={i}
              className={`flex gap-2 px-3 py-0.5 font-mono text-xs ${lineClass(line.type)}`}
            >
              <span className="text-slate-300 select-none w-6 text-right shrink-0">{i + 1}</span>
              <span className="text-slate-700 dark:text-slate-300 whitespace-pre-wrap break-all">
                {line.text || '\u00A0'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* 범례 */}
      <div className="flex gap-4 px-4 py-2 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-green-400" />
          추가
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-red-400" />
          제거
        </span>
      </div>
    </div>
  );
}
