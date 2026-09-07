import { describe, expect, it } from 'vitest';

import {
  buildCircularGraphLayout,
  connectedNodeIds,
  type NoteGraphNode,
} from './note-graph';

const node = (id: string): NoteGraphNode => ({
  id,
  title: `note-${id}`,
  key_concepts: [],
  created_at: '',
});

describe('note graph helpers', () => {
  it('places one node at the center and many nodes deterministically', () => {
    expect(buildCircularGraphLayout([node('a')])).toEqual([
      { ...node('a'), x: 50, y: 50 },
    ]);

    const first = buildCircularGraphLayout([node('a'), node('b'), node('c')]);
    const second = buildCircularGraphLayout([node('a'), node('b'), node('c')]);
    expect(second).toEqual(first);
    expect(first.every((point) => point.x >= 0 && point.x <= 100)).toBe(true);
    expect(first.every((point) => point.y >= 0 && point.y <= 100)).toBe(true);
  });

  it('collects both incoming and outgoing neighbours for focus highlighting', () => {
    const ids = connectedNodeIds('b', [
      { source: 'a', target: 'b', score: 0.8 },
      { source: 'b', target: 'c', score: 0.7 },
      { source: 'x', target: 'y', score: 0.9 },
    ]);

    expect([...ids].sort()).toEqual(['a', 'b', 'c']);
  });
});
