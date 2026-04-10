/**
 * 커스텀 리포트 빌더 (F6-17)
 * 드래그앤드롭으로 차트 조합하여 대시보드 구성
 */
'use client';

import React, { useState, useRef } from 'react';

type ChartType = 'line' | 'bar' | 'pie' | 'table';

interface ChartBlock {
  id: string;
  type: ChartType;
  metric: string;
  title: string;
}

const AVAILABLE_METRICS = [
  { key: 'daily_generations', label: '일별 생성 수', defaultChart: 'line' as ChartType },
  { key: 'style_distribution', label: '스타일 분포', defaultChart: 'pie' as ChartType },
  { key: 'model_benchmark', label: '모델 성능', defaultChart: 'bar' as ChartType },
  { key: 'cost_trend', label: '비용 추세', defaultChart: 'line' as ChartType },
  { key: 'quality_trend', label: '품질 점수', defaultChart: 'line' as ChartType },
];

export function ReportBuilder() {
  const [blocks, setBlocks] = useState<ChartBlock[]>([]);
  const [draggingOver, setDraggingOver] = useState<string | null>(null);
  const idCounter = useRef(0);

  const addBlock = (metric: { key: string; label: string; defaultChart: ChartType }) => {
    const newBlock: ChartBlock = {
      id: `${metric.key}-${++idCounter.current}`,
      type: metric.defaultChart,
      metric: metric.key,
      title: metric.label,
    };
    setBlocks((prev) => [...prev, newBlock]);
  };

  const removeBlock = (id: string) => {
    setBlocks((prev) => prev.filter((b) => b.id !== id));
  };

  const changeChartType = (id: string, type: ChartType) => {
    setBlocks((prev) =>
      prev.map((b) => (b.id === id ? { ...b, type } : b))
    );
  };

  const handleDragStart = (e: React.DragEvent, id: string) => {
    e.dataTransfer.setData('blockId', id);
  };

  const handleDrop = (e: React.DragEvent, targetId: string) => {
    e.preventDefault();
    const sourceId = e.dataTransfer.getData('blockId');
    if (sourceId === targetId) return;
    setBlocks((prev) => {
      const sourceIdx = prev.findIndex((b) => b.id === sourceId);
      const targetIdx = prev.findIndex((b) => b.id === targetId);
      if (sourceIdx < 0 || targetIdx < 0) return prev;
      const next = [...prev];
      [next[sourceIdx], next[targetIdx]] = [next[targetIdx], next[sourceIdx]];
      return next;
    });
    setDraggingOver(null);
  };

  return (
    <div className="flex gap-4 p-4">
      {/* 사이드바: 추가 가능한 메트릭 */}
      <aside className="w-56 shrink-0 rounded-lg border p-4">
        <h3 className="mb-3 font-semibold text-sm">지표 선택</h3>
        <ul className="space-y-2">
          {AVAILABLE_METRICS.map((m) => (
            <li key={m.key}>
              <button
                onClick={() => addBlock(m)}
                aria-label={`${m.label} 지표 추가`}
                className="w-full text-left rounded px-2 py-1 text-sm hover:bg-muted transition-colors"
              >
                + {m.label}
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* 캔버스 */}
      <main className="flex-1 min-h-64 rounded-lg border-2 border-dashed p-4">
        {blocks.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            왼쪽에서 지표를 추가하세요
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {blocks.map((block) => (
              <div
                key={block.id}
                draggable
                onDragStart={(e) => handleDragStart(e, block.id)}
                onDragOver={(e) => { e.preventDefault(); setDraggingOver(block.id); }}
                onDrop={(e) => handleDrop(e, block.id)}
                onDragLeave={() => setDraggingOver(null)}
                className={`rounded-lg border bg-card p-3 cursor-move transition-shadow ${
                  draggingOver === block.id ? 'shadow-lg ring-2 ring-primary' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">{block.title}</span>
                  <button
                    onClick={() => removeBlock(block.id)}
                    aria-label={`${block.title} 블록 제거`}
                    className="text-muted-foreground hover:text-destructive text-xs"
                  >
                    ✕
                  </button>
                </div>
                {/* 차트 타입 선택 */}
                <select
                  value={block.type}
                  onChange={(e) => changeChartType(block.id, e.target.value as ChartType)}
                  className="text-xs border rounded px-1 py-0.5 mb-2 w-full"
                >
                  <option value="line">선형 차트</option>
                  <option value="bar">막대 차트</option>
                  <option value="pie">파이 차트</option>
                  <option value="table">테이블</option>
                </select>
                {/* 차트 플레이스홀더 */}
                <div className="h-24 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground">
                  [{block.type.toUpperCase()}] {block.metric}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
