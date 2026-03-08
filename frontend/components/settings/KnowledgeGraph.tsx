'use client';

import { useState, useCallback, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface GraphNode {
  name: string;
  type: string;
  description: string;
  degree?: number;
  is_center?: boolean;
}

interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  weight: number;
}

interface GraphData {
  nodes: GraphNode[];
  edges?: GraphEdge[];
  stats: { node_count: number; edge_count: number };
}

const TYPE_COLORS: Record<string, string> = {
  person: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  organization: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  technology: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  concept: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  product: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  location: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
};

export default function KnowledgeGraph() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [subgraph, setSubgraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] } | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchGraph = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/knowledge/graph');
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
      }
    } catch {
      // 그래프 미사용 시 무시
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchSubgraph = useCallback(async (entity: string) => {
    try {
      const res = await fetch(`/api/knowledge/graph/subgraph?entity=${encodeURIComponent(entity)}`);
      if (res.ok) {
        const data = await res.json();
        setSubgraph(data);
      }
    } catch {
      // 무시
    }
  }, []);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const handleNodeClick = (name: string) => {
    setSelectedNode(name);
    fetchSubgraph(name);
  };

  if (isLoading) {
    return <div className="text-sm text-muted-foreground p-4">지식 그래프 로딩 중...</div>;
  }

  if (!graphData || graphData.stats.node_count === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4">
        지식 그래프가 비어있습니다. 문서를 업로드하면 자동으로 엔티티가 추출됩니다.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 통계 */}
      <div className="flex gap-4 text-sm">
        <span className="text-muted-foreground">
          노드 <span className="font-medium text-foreground">{graphData.stats.node_count}</span>개
        </span>
        <span className="text-muted-foreground">
          관계 <span className="font-medium text-foreground">{graphData.stats.edge_count}</span>개
        </span>
      </div>

      {/* 주요 노드 목록 */}
      <div className="space-y-2">
        <h4 className="text-sm font-medium">주요 엔티티 (연결 수 기준)</h4>
        <div className="flex flex-wrap gap-2">
          {graphData.nodes.map((node) => (
            <button
              key={node.name}
              onClick={() => handleNodeClick(node.name)}
              aria-label={`${node.name} 엔티티 선택`}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-medium transition-colors cursor-pointer',
                TYPE_COLORS[node.type] ?? TYPE_COLORS.concept,
                selectedNode === node.name && 'ring-2 ring-primary',
              )}
              title={node.description || node.name}
            >
              {node.name}
              {node.degree !== undefined && (
                <span className="ml-1 opacity-60">({node.degree})</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* 선택된 노드의 서브그래프 */}
      {selectedNode && subgraph && (
        <div className="rounded-lg border p-3 space-y-2">
          <h4 className="text-sm font-medium">&quot;{selectedNode}&quot; 관계 네트워크</h4>

          {subgraph.edges.length > 0 ? (
            <div className="space-y-1">
              {subgraph.edges.map((edge, idx) => (
                <div key={idx} className="text-xs text-muted-foreground flex items-center gap-1">
                  <span className="font-medium text-foreground">{edge.source}</span>
                  <span className="text-primary">--[{edge.relation}]--&gt;</span>
                  <span className="font-medium text-foreground">{edge.target}</span>
                  <span className="opacity-50">({Math.round(edge.weight * 100)}%)</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">연결된 관계가 없습니다.</div>
          )}
        </div>
      )}
    </div>
  );
}
