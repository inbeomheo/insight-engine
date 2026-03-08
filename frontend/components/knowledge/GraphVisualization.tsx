/**
 * 지식 그래프 시각화 컴포넌트 (F10-11)
 * D3.js Force Simulation 기반 인터랙티브 그래프
 * RAG 지식베이스의 문서 관계를 시각화
 */
'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { apiUrl } from '@/lib/api';

// ── 타입 정의 ─────────────────────────────────────────────────────────────────

export interface GraphNode {
  id: string;
  label: string;
  type: 'document' | 'concept' | 'entity' | 'topic';
  size?: number;         // 노드 크기 (연결 수 비례)
  score?: number;        // 관련도 점수 (0~1)
  metadata?: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight?: number;       // 연결 강도 (0~1)
  label?: string;        // 관계 레이블
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface GraphVisualizationProps {
  data: GraphData;
  width?: number;
  height?: number;
  onNodeClick?: (node: GraphNode) => void;
  className?: string;
}

// ── 색상 팔레트 ───────────────────────────────────────────────────────────────

const NODE_COLORS: Record<GraphNode['type'], string> = {
  document: '#6366f1',   // Indigo
  concept: '#10b981',    // Emerald
  entity: '#f59e0b',     // Amber
  topic: '#ef4444',      // Red
};

// ── SVG 기반 간단 구현 (D3 없이) ─────────────────────────────────────────────
// 실제 프로덕션에서는 d3-force 또는 react-force-graph 사용 권장

function simpleLayout(nodes: GraphNode[], edges: GraphEdge[], width: number, height: number) {
  // 원형 배치 (force simulation 미적용 간단 버전)
  const positions: Record<string, { x: number; y: number }> = {};
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.35;

  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    positions[node.id] = {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    };
  });

  return positions;
}

// ── 컴포넌트 ──────────────────────────────────────────────────────────────────

export function GraphVisualization({
  data,
  width = 800,
  height = 500,
  onNodeClick,
  className = '',
}: GraphVisualizationProps) {
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!data.nodes.length) return;
    const pos = simpleLayout(data.nodes, data.edges, width, height);
    setPositions(pos);
  }, [data, width, height]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node.id === selectedNode ? null : node.id);
    onNodeClick?.(node);
  }, [selectedNode, onNodeClick]);

  if (!data.nodes.length) {
    return (
      <div className={`flex items-center justify-center bg-gray-50 dark:bg-gray-900 rounded-lg ${className}`}
           style={{ width, height }}>
        <p className="text-gray-500 text-sm">지식 그래프 데이터가 없습니다</p>
      </div>
    );
  }

  return (
    <div className={`relative bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 ${className}`}>
      {/* 범례 */}
      <div className="absolute top-3 left-3 flex flex-col gap-1 z-10">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="capitalize">{type}</span>
          </div>
        ))}
      </div>

      {/* 선택 노드 정보 */}
      {selectedNode && (
        <div className="absolute top-3 right-3 z-10 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 max-w-xs">
          {(() => {
            const node = data.nodes.find(n => n.id === selectedNode);
            if (!node) return null;
            return (
              <>
                <p className="font-medium text-sm text-gray-900 dark:text-white">{node.label}</p>
                <p className="text-xs text-gray-500 capitalize mt-1">{node.type}</p>
                {node.score !== undefined && (
                  <p className="text-xs text-indigo-600 dark:text-indigo-400 mt-1">
                    관련도: {(node.score * 100).toFixed(0)}%
                  </p>
                )}
              </>
            );
          })()}
        </div>
      )}

      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="w-full h-full"
        viewBox={`0 0 ${width} ${height}`}
      >
        {/* 엣지 렌더링 */}
        <g className="edges">
          {data.edges.map((edge, i) => {
            const src = positions[edge.source];
            const tgt = positions[edge.target];
            if (!src || !tgt) return null;
            const isHighlighted = hoveredNode &&
              (edge.source === hoveredNode || edge.target === hoveredNode);
            return (
              <line
                key={i}
                x1={src.x} y1={src.y}
                x2={tgt.x} y2={tgt.y}
                stroke={isHighlighted ? '#6366f1' : '#d1d5db'}
                strokeWidth={isHighlighted ? 2 : 1}
                strokeOpacity={isHighlighted ? 0.8 : 0.4}
                style={{ transition: 'stroke 0.2s, stroke-opacity 0.2s' }}
              />
            );
          })}
        </g>

        {/* 노드 렌더링 */}
        <g className="nodes">
          {data.nodes.map(node => {
            const pos = positions[node.id];
            if (!pos) return null;
            const r = 6 + (node.size || 1) * 2;
            const color = NODE_COLORS[node.type] || '#6366f1';
            const isHovered = hoveredNode === node.id;
            const isSelected = selectedNode === node.id;

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x},${pos.y})`}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => handleNodeClick(node)}
              >
                <circle
                  r={isSelected ? r + 4 : isHovered ? r + 2 : r}
                  fill={color}
                  fillOpacity={isHovered || isSelected ? 1 : 0.8}
                  stroke={isSelected ? '#fff' : 'none'}
                  strokeWidth={isSelected ? 2 : 0}
                  style={{ transition: 'r 0.15s, fill-opacity 0.15s' }}
                />
                <text
                  dy={r + 14}
                  textAnchor="middle"
                  fontSize={10}
                  fill="currentColor"
                  className="fill-gray-600 dark:fill-gray-300"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  {node.label.length > 15 ? node.label.slice(0, 15) + '…' : node.label}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

// ── 컨테이너 컴포넌트 (API 연동) ──────────────────────────────────────────────

export function KnowledgeGraphPanel({ className = '' }: { className?: string }) {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(apiUrl('/api/knowledge/graph'));
      if (!resp.ok) throw new Error(`API 오류: ${resp.status}`);
      const data = await resp.json();
      setGraphData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : '그래프 로드 실패');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-900 dark:text-white">지식 그래프</h3>
        <button
          onClick={fetchGraph}
          disabled={loading}
          aria-label="지식 그래프 새로고침"
          className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-50"
        >
          {loading ? '로딩 중…' : '새로고침'}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}

      <GraphVisualization
        data={graphData}
        height={400}
        className={loading ? 'opacity-50' : ''}
      />

      <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
        노드: {graphData.nodes.length}개 | 연결: {graphData.edges.length}개
      </p>
    </div>
  );
}
