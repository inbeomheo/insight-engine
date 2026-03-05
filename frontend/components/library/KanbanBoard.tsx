'use client';

/**
 * KanbanBoard — 콘텐츠 상태 관리 칸반 보드 (F8-04)
 *
 * 상태(draft → review → approved → published)를 열(column)로 표시하고
 * 카드 드래그를 시뮬레이션합니다. (HTML5 drag & drop 기반)
 */

import React, { useState, useCallback } from 'react';

export type KanbanStatus = 'draft' | 'review' | 'approved' | 'published' | 'archived';

export interface KanbanCard {
  id: string;
  title: string;
  style?: string;
  tags?: string[];
  updated_at?: string;
  status: KanbanStatus;
}

const COLUMNS: { key: KanbanStatus; label: string; color: string }[] = [
  { key: 'draft',     label: '초안',    color: 'bg-slate-100 dark:bg-slate-800' },
  { key: 'review',   label: '검토 중', color: 'bg-yellow-50 dark:bg-yellow-900/20' },
  { key: 'approved', label: '승인됨',  color: 'bg-green-50 dark:bg-green-900/20' },
  { key: 'published',label: '발행됨',  color: 'bg-blue-50 dark:bg-blue-900/20' },
  { key: 'archived', label: '아카이브', color: 'bg-gray-50 dark:bg-gray-900/20' },
];

interface Props {
  cards: KanbanCard[];
  onStatusChange?: (cardId: string, newStatus: KanbanStatus) => void;
  onCardClick?: (card: KanbanCard) => void;
}

export default function KanbanBoard({ cards, onStatusChange, onCardClick }: Props) {
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [overColumn, setOverColumn] = useState<KanbanStatus | null>(null);

  const byStatus = useCallback(
    (status: KanbanStatus) => cards.filter((c) => c.status === status),
    [cards],
  );

  const handleDragStart = (e: React.DragEvent, cardId: string) => {
    e.dataTransfer.setData('cardId', cardId);
    setDraggingId(cardId);
  };

  const handleDrop = (e: React.DragEvent, status: KanbanStatus) => {
    e.preventDefault();
    const cardId = e.dataTransfer.getData('cardId');
    if (cardId && onStatusChange) {
      onStatusChange(cardId, status);
    }
    setDraggingId(null);
    setOverColumn(null);
  };

  const handleDragOver = (e: React.DragEvent, status: KanbanStatus) => {
    e.preventDefault();
    setOverColumn(status);
  };

  return (
    <div className="flex gap-3 overflow-x-auto pb-4">
      {COLUMNS.map((col) => {
        const colCards = byStatus(col.key);
        const isOver = overColumn === col.key;
        return (
          <div
            key={col.key}
            className={`
              flex-shrink-0 w-60 rounded-xl border-2 transition-colors
              ${col.color}
              ${isOver ? 'border-blue-400 dark:border-blue-500' : 'border-transparent'}
            `}
            onDrop={(e) => handleDrop(e, col.key)}
            onDragOver={(e) => handleDragOver(e, col.key)}
            onDragLeave={() => setOverColumn(null)}
          >
            {/* 열 헤더 */}
            <div className="px-3 py-2 flex items-center justify-between border-b border-slate-200 dark:border-slate-700">
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                {col.label}
              </span>
              <span className="text-xs text-slate-500 bg-slate-200 dark:bg-slate-700 rounded-full px-2 py-0.5">
                {colCards.length}
              </span>
            </div>

            {/* 카드 목록 */}
            <div className="p-2 flex flex-col gap-2 min-h-24">
              {colCards.map((card) => (
                <div
                  key={card.id}
                  draggable
                  onDragStart={(e) => handleDragStart(e, card.id)}
                  onClick={() => onCardClick?.(card)}
                  className={`
                    bg-white dark:bg-slate-800 rounded-lg p-3 shadow-sm border
                    border-slate-200 dark:border-slate-700 cursor-grab
                    hover:shadow-md transition-shadow text-sm
                    ${draggingId === card.id ? 'opacity-40' : ''}
                  `}
                >
                  <p className="font-medium text-slate-800 dark:text-slate-100 line-clamp-2">
                    {card.title}
                  </p>
                  {card.style && (
                    <span className="mt-1 inline-block text-xs text-slate-400 bg-slate-100 dark:bg-slate-700 rounded px-1">
                      {card.style}
                    </span>
                  )}
                  {card.tags && card.tags.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {card.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="text-xs text-blue-600 dark:text-blue-400"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
