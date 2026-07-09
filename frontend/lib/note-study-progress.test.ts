import { describe, expect, it } from 'vitest';
import {
  buildNoteStudyMarkdown,
  clearNoteStudyProgress,
  getNoteStudyProgressKey,
  getNoteStudySummary,
  getVisibleNoteStudyIndexes,
  normalizeNoteStudyProgress,
  readNoteStudyProgress,
  toggleNoteStudyItem,
  writeNoteStudyProgress,
  type NoteStudyProgress,
} from './note-study-progress';

function createMemoryStorage() {
  const data = new Map<string, string>();
  return {
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => data.set(key, value),
    removeItem: (key: string) => data.delete(key),
  };
}

describe('note-study-progress', () => {
  it('normalizes invalid and out-of-range indexes', () => {
    expect(
      normalizeNoteStudyProgress(
        {
          learning: [2, 1, 1, -1, 99, 'x'],
          review: [0, 3, 2],
          updatedAt: '2026-07-10T00:00:00.000Z',
        },
        { learning: 3, review: 2 }
      )
    ).toEqual({
      learning: [1, 2],
      review: [0],
      updatedAt: '2026-07-10T00:00:00.000Z',
    });
  });

  it('toggles learning and review progress with a stable summary', () => {
    const empty: NoteStudyProgress = { learning: [], review: [], updatedAt: null };
    const first = toggleNoteStudyItem(empty, 'learning', 1, { learning: 3, review: 2 }, 'now');
    const second = toggleNoteStudyItem(first, 'review', 0, { learning: 3, review: 2 }, 'later');

    expect(second).toEqual({ learning: [1], review: [0], updatedAt: 'later' });
    expect(getNoteStudySummary(second, { learning: 3, review: 2 })).toEqual({
      completed: 2,
      total: 5,
      percent: 40,
      completedLearning: 1,
      completedReview: 1,
    });
    expect(toggleNoteStudyItem(second, 'learning', 1, { learning: 3, review: 2 }, 'done').learning).toEqual([]);
  });

  it('persists progress in the provided storage', () => {
    const storage = createMemoryStorage();
    const progress: NoteStudyProgress = {
      learning: [0],
      review: [1],
      updatedAt: '2026-07-10T00:00:00.000Z',
    };

    writeNoteStudyProgress('note-1', progress, { learning: 2, review: 2 }, storage);

    expect(storage.getItem(getNoteStudyProgressKey('note-1'))).toContain('2026-07-10');
    expect(readNoteStudyProgress('note-1', { learning: 2, review: 2 }, storage)).toEqual(progress);

    clearNoteStudyProgress('note-1', storage);
    expect(readNoteStudyProgress('note-1', { learning: 2, review: 2 }, storage)).toEqual({
      learning: [],
      review: [],
      updatedAt: null,
    });
  });

  it('returns visible study indexes for all or unfinished-only mode', () => {
    expect(getVisibleNoteStudyIndexes(4, [2, 0, 99], true)).toEqual([0, 1, 2, 3]);
    expect(getVisibleNoteStudyIndexes(4, [2, 0, 99], false)).toEqual([1, 3]);
    expect(getVisibleNoteStudyIndexes(-1, [0], false)).toEqual([]);
  });

  it('builds markdown with checked study items and review answers', () => {
    expect(
      buildNoteStudyMarkdown({
        title: '테스트 노트',
        sourceUrl: 'https://example.com/video',
        learningPoints: ['핵심 개념 정리', '실습으로 확인'],
        reviewQuestions: [
          { question: '첫 질문은?', answer: '첫 답변' },
          { question: '둘째 질문은?' },
        ],
        progress: {
          learning: [1],
          review: [0],
          updatedAt: '2026-07-10T00:00:00.000Z',
        },
      })
    ).toBe([
      '# 테스트 노트 복습 노트',
      '',
      '- 진행률: 2/4 (50%)',
      '- 원본: https://example.com/video',
      '- 마지막 체크: 2026-07-10T00:00:00.000Z',
      '',
      '## 학습 포인트',
      '- [ ] 핵심 개념 정리',
      '- [x] 실습으로 확인',
      '',
      '## 복습 질문',
      '- [x] 첫 질문은?',
      '  - 답: 첫 답변',
      '- [ ] 둘째 질문은?',
      '',
    ].join('\n'));
  });
});
