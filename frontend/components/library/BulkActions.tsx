'use client';

/**
 * BulkActions — 콘텐츠 일괄 작업 툴바 (F8-05)
 *
 * 선택된 항목에 대해 일괄 삭제, 아카이브, 태그 추가, 상태 변경을 수행합니다.
 */

import React, { useState } from 'react';
import { Trash2, Archive, Tag, RefreshCw } from 'lucide-react';

export type BulkActionType = 'delete' | 'archive' | 'tag' | 'status_change';

export interface BulkResult {
  success_count: number;
  failed_count: number;
  success: string[];
  failed: string[];
}

interface Props {
  selectedIds: string[];
  onClearSelection: () => void;
  onSuccess?: (action: BulkActionType, result: BulkResult) => void;
  className?: string;
}

const STATUS_OPTIONS = ['draft', 'review', 'approved', 'published', 'archived'];

export default function BulkActions({ selectedIds, onClearSelection, onSuccess, className }: Props) {
  const [loading, setLoading] = useState(false);
  const [tagInput, setTagInput] = useState('');
  const [showTagInput, setShowTagInput] = useState(false);
  const [showStatusSelect, setShowStatusSelect] = useState(false);

  if (selectedIds.length === 0) return null;

  const runAction = async (action: BulkActionType, extra: Record<string, unknown> = {}) => {
    setLoading(true);
    try {
      const res = await fetch('/api/content/bulk', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, item_ids: selectedIds, ...extra }),
      });
      const data: BulkResult & { action: string } = await res.json();
      onSuccess?.(action, data);
      onClearSelection();
    } catch {
      // 에러는 부모에서 처리
    } finally {
      setLoading(false);
      setShowTagInput(false);
      setShowStatusSelect(false);
    }
  };

  return (
    <div
      className={`
        flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl shadow-lg
        ${className ?? ''}
      `}
    >
      <span className="text-sm font-medium mr-2">
        {selectedIds.length}개 선택됨
      </span>

      {/* 삭제 */}
      <button
        disabled={loading}
        onClick={() => runAction('delete')}
        className="flex items-center gap-1 text-xs px-2 py-1 bg-red-500 hover:bg-red-600 rounded-lg transition-colors disabled:opacity-50"
      >
        <Trash2 className="w-3 h-3" />
        삭제
      </button>

      {/* 아카이브 */}
      <button
        disabled={loading}
        onClick={() => runAction('archive')}
        className="flex items-center gap-1 text-xs px-2 py-1 bg-white/20 hover:bg-white/30 rounded-lg transition-colors disabled:opacity-50"
      >
        <Archive className="w-3 h-3" />
        아카이브
      </button>

      {/* 태그 추가 */}
      {showTagInput ? (
        <div className="flex items-center gap-1">
          <input
            type="text"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="태그 (쉼표 구분)"
            className="text-xs px-2 py-1 rounded text-slate-900 w-32"
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const tags = tagInput.split(',').map((t) => t.trim()).filter(Boolean);
                runAction('tag', { tags });
              }
              if (e.key === 'Escape') setShowTagInput(false);
            }}
            autoFocus
          />
        </div>
      ) : (
        <button
          disabled={loading}
          onClick={() => setShowTagInput(true)}
          className="flex items-center gap-1 text-xs px-2 py-1 bg-white/20 hover:bg-white/30 rounded-lg transition-colors disabled:opacity-50"
        >
          <Tag className="w-3 h-3" />
          태그
        </button>
      )}

      {/* 상태 변경 */}
      {showStatusSelect ? (
        <select
          className="text-xs px-2 py-1 rounded text-slate-900"
          defaultValue=""
          onChange={(e) => {
            if (e.target.value) runAction('status_change', { status: e.target.value });
          }}
          autoFocus
        >
          <option value="" disabled>상태 선택</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      ) : (
        <button
          disabled={loading}
          onClick={() => setShowStatusSelect(true)}
          className="flex items-center gap-1 text-xs px-2 py-1 bg-white/20 hover:bg-white/30 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className="w-3 h-3" />
          상태 변경
        </button>
      )}

      {/* 선택 해제 */}
      <button
        onClick={onClearSelection}
        className="ml-auto text-xs px-2 py-1 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
      >
        선택 해제
      </button>
    </div>
  );
}
