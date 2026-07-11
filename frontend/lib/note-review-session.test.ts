import { describe, expect, it } from 'vitest';
import {
  createReviewAnswerVisibility,
  normalizeReviewAnswerVisibility,
  setAllReviewAnswersVisible,
  toggleReviewAnswerVisibility,
} from './note-review-session';

describe('note-review-session', () => {
  it('creates and normalizes answer visibility state by question count', () => {
    expect(createReviewAnswerVisibility(3)).toEqual([false, false, false]);
    expect(createReviewAnswerVisibility(2, true)).toEqual([true, true]);
    expect(normalizeReviewAnswerVisibility([true, false, true], 2)).toEqual([true, false]);
    expect(normalizeReviewAnswerVisibility(['yes', true], 3)).toEqual([false, true, false]);
  });

  it('toggles only valid review answer indexes', () => {
    expect(toggleReviewAnswerVisibility([false, true], 0, 2)).toEqual([true, true]);
    expect(toggleReviewAnswerVisibility([false, true], 5, 2)).toEqual([false, true]);
  });

  it('sets all review answers to one visibility state', () => {
    expect(setAllReviewAnswersVisible(3, true)).toEqual([true, true, true]);
    expect(setAllReviewAnswersVisible(2, false)).toEqual([false, false]);
  });
});
