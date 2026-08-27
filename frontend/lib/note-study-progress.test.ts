import { describe, expect, it } from 'vitest';
import {
  buildNextNoteStudyTargetMarkdown,
  buildNoteStudyMarkdown,
  clearNoteStudyProgress,
  getNextNoteStudyTarget,
  getNoteStudyCompletionSummary,
  getNoteStudyProgressKey,
  getNoteStudySummary,
  getVisibleNoteStudyIndexes,
  normalizeNoteStudyProgress,
  readNoteStudyProgress,
  toggleNoteStudyItem,
  writeNoteStudyProgress,
  type NoteStudyProgress,
} from './note-study-progress';
import { setAuthSession, type AuthSession } from './auth-session';

function authSession(userId: string): AuthSession {
  return { user: { id: userId }, session: { access_token: `${userId}-token` } };
}

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

  it('summarizes completion states for review sessions', () => {
    expect(getNoteStudyCompletionSummary({
      completed: 0,
      total: 0,
      percent: 0,
      completedLearning: 0,
      completedReview: 0,
    })).toEqual({
      complete: false,
      remaining: 0,
      message: '복습 항목이 없습니다.',
      actionLabel: '복습 시작',
    });
    expect(getNoteStudyCompletionSummary({
      completed: 0,
      total: 3,
      percent: 0,
      completedLearning: 0,
      completedReview: 0,
    })).toEqual({
      complete: false,
      remaining: 3,
      message: '아직 복습을 시작하지 않았습니다.',
      actionLabel: '복습 시작',
    });
    expect(getNoteStudyCompletionSummary({
      completed: 2,
      total: 3,
      percent: 67,
      completedLearning: 1,
      completedReview: 1,
    })).toEqual({
      complete: false,
      remaining: 1,
      message: '남은 복습 항목 1개',
      actionLabel: '이어 복습',
    });
    expect(getNoteStudyCompletionSummary({
      completed: 3,
      total: 3,
      percent: 100,
      completedLearning: 2,
      completedReview: 1,
    })).toEqual({
      complete: true,
      remaining: 0,
      message: '모든 복습 항목을 완료했습니다.',
      actionLabel: '다시 복습',
    });
  });

  it('finds the next unfinished learning point before review questions', () => {
    expect(
      getNextNoteStudyTarget({
        learningPoints: ['첫 개념', '둘째 개념'],
        reviewQuestions: [{ question: '첫 질문은?' }],
        progress: { learning: [0], review: [], updatedAt: null },
      })
    ).toEqual({
      kind: 'learning',
      index: 1,
      label: '학습 포인트 2',
      title: '둘째 개념',
      description: '먼저 핵심 내용을 확인하고 체크하세요.',
      targetId: 'study-learning-1',
    });
  });

  it('falls back to the first unfinished review question after learning points', () => {
    expect(
      getNextNoteStudyTarget({
        learningPoints: ['첫 개념'],
        reviewQuestions: [{ question: '첫 질문은?' }, { question: '둘째 질문은?' }],
        progress: { learning: [0], review: [0], updatedAt: null },
      })
    ).toEqual({
      kind: 'review',
      index: 1,
      label: '복습 질문 2',
      title: '둘째 질문은?',
      description: '답을 떠올린 뒤 열어보고 체크하세요.',
      targetId: 'study-review-1',
    });
  });

  it('returns no next target when every study item is complete', () => {
    expect(
      getNextNoteStudyTarget({
        learningPoints: ['첫 개념'],
        reviewQuestions: [{ question: '첫 질문은?' }],
        progress: { learning: [0, 99], review: [0], updatedAt: null },
      })
    ).toBeNull();
    expect(
      getNextNoteStudyTarget({
        progress: { learning: [], review: [], updatedAt: null },
      })
    ).toBeNull();
  });

  it('builds markdown for the next study target', () => {
    const target = getNextNoteStudyTarget({
      learningPoints: ['  핵심\n개념  '],
      reviewQuestions: [],
      progress: { learning: [], review: [], updatedAt: null },
    });

    expect(buildNextNoteStudyTargetMarkdown({
      noteTitle: '  노트\n제목  ',
      target,
    })).toBe([
      '# 다음 복습: 노트 제목',
      '',
      '- 항목: 학습 포인트 1',
      '- 내용: 핵심 개념',
      '- 안내: 먼저 핵심 내용을 확인하고 체크하세요.',
      '- 위치: #study-learning-0',
    ].join('\n'));

    expect(buildNextNoteStudyTargetMarkdown({ noteTitle: '', target: null })).toBe(
      '# 다음 복습: 제목 없음\n\n남은 복습 항목이 없습니다.'
    );
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

  it('계정별로 같은 노트의 학습 진행률을 격리한다', () => {
    const storage = createMemoryStorage();
    const counts = { learning: 2, review: 2 };
    try {
      setAuthSession(authSession('account-a'));
      writeNoteStudyProgress(
        'shared-note',
        { learning: [0], review: [], updatedAt: '2026-07-10T00:00:00.000Z' },
        counts,
        storage,
      );

      setAuthSession(authSession('account-b'));
      expect(readNoteStudyProgress('shared-note', counts, storage).learning).toEqual([]);
      writeNoteStudyProgress(
        'shared-note',
        { learning: [1], review: [0], updatedAt: '2026-07-11T00:00:00.000Z' },
        counts,
        storage,
      );

      setAuthSession(authSession('account-a'));
      expect(readNoteStudyProgress('shared-note', counts, storage)).toMatchObject({
        learning: [0],
        review: [],
      });
    } finally {
      setAuthSession(null);
    }
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
