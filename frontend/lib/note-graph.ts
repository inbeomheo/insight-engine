import { isApiError, request } from '@/lib/api';

export interface NoteGraphNode {
  id: string;
  title: string;
  key_concepts: string[];
  created_at: string;
}

export interface NoteGraphEdge {
  source: string;
  target: string;
  score: number;
}

export interface NoteGraphResponse {
  nodes: NoteGraphNode[];
  edges: NoteGraphEdge[];
  meta: {
    node_limit: number;
    edge_limit: number;
    related_limit: number;
    min_score: number;
    node_count: number;
    edge_count: number;
  };
}

export interface NoteBacklink {
  id: string;
  title: string;
  score: number;
}

export interface NoteGraphPoint extends NoteGraphNode {
  x: number;
  y: number;
}

async function readJson<T>(path: string): Promise<T> {
  try {
    return await request<T>(path);
  } catch (error) {
    if (isApiError(error) && (error.status === 401 || error.status === 403)) {
      throw new Error('로그인이 필요합니다.');
    }
    throw error;
  }
}

export async function getNoteGraph(): Promise<NoteGraphResponse> {
  return readJson<NoteGraphResponse>('/api/notes/graph');
}

export async function getNoteBacklinks(noteId: string): Promise<{ notes: NoteBacklink[] }> {
  return readJson<{ notes: NoteBacklink[] }>(
    `/api/notes/${encodeURIComponent(noteId)}/backlinks`,
  );
}

export function buildCircularGraphLayout(nodes: NoteGraphNode[]): NoteGraphPoint[] {
  if (nodes.length === 0) return [];
  if (nodes.length === 1) return [{ ...nodes[0], x: 50, y: 50 }];

  const radius = nodes.length <= 8 ? 34 : nodes.length <= 20 ? 39 : 43;
  return nodes.map((node, index) => {
    const angle = (Math.PI * 2 * index) / nodes.length - Math.PI / 2;
    return {
      ...node,
      x: Number((50 + Math.cos(angle) * radius).toFixed(3)),
      y: Number((50 + Math.sin(angle) * radius).toFixed(3)),
    };
  });
}

export function connectedNodeIds(
  nodeId: string,
  edges: NoteGraphEdge[],
): Set<string> {
  const ids = new Set<string>([nodeId]);
  for (const edge of edges) {
    if (edge.source === nodeId) ids.add(edge.target);
    if (edge.target === nodeId) ids.add(edge.source);
  }
  return ids;
}
