export function createReviewAnswerVisibility(count: number, visible = false): boolean[] {
  return Array.from({ length: Math.max(0, count) }, () => visible);
}

export function normalizeReviewAnswerVisibility(value: unknown, count: number): boolean[] {
  const length = Math.max(0, count);
  if (!Array.isArray(value)) return createReviewAnswerVisibility(length);
  return createReviewAnswerVisibility(length).map((_, index) => value[index] === true);
}

export function toggleReviewAnswerVisibility(value: unknown, index: number, count: number): boolean[] {
  const next = normalizeReviewAnswerVisibility(value, count);
  if (!Number.isInteger(index) || index < 0 || index >= next.length) return next;
  next[index] = !next[index];
  return next;
}

export function setAllReviewAnswersVisible(count: number, visible: boolean): boolean[] {
  return createReviewAnswerVisibility(count, visible);
}
