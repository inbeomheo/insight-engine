export interface NoteOutlineInput {
  key_concepts?: unknown[];
  learning_points?: unknown[];
  review_questions?: unknown[];
  summary?: string | null;
  quotes?: unknown[];
  related_notes?: unknown[];
}

export interface NoteOutlineItem {
  id: string;
  label: string;
  count?: number;
}

export function buildNoteOutline(
  note: NoteOutlineInput,
  options: { hasLinkedReport?: boolean } = {}
): NoteOutlineItem[] {
  const keyConceptCount = note.key_concepts?.length ?? 0;
  const learningPointCount = note.learning_points?.length ?? 0;
  const reviewQuestionCount = note.review_questions?.length ?? 0;
  const quoteCount = note.quotes?.length ?? 0;
  const relatedNoteCount = note.related_notes?.length ?? 0;

  const items: NoteOutlineItem[] = [{ id: 'source', label: '출처' }];

  if (options.hasLinkedReport) {
    items.push({ id: 'source-result', label: '원본 결과' });
  }
  items.push({ id: 'wiki-brief', label: '문서 브리핑' });
  if (learningPointCount + reviewQuestionCount > 0) {
    items.push({ id: 'study-progress', label: '복습 진행', count: learningPointCount + reviewQuestionCount });
  }
  if (keyConceptCount > 0) {
    items.push({ id: 'concepts', label: '핵심 개념', count: keyConceptCount });
  }
  if (learningPointCount > 0) {
    items.push({ id: 'learning-points', label: '학습 포인트', count: learningPointCount });
  }
  if (reviewQuestionCount > 0) {
    items.push({ id: 'review-questions', label: '복습 질문', count: reviewQuestionCount });
  }
  if (note.summary?.trim()) {
    items.push({ id: 'summary', label: '요약' });
  }

  items.push({ id: 'chat', label: '근거 Q&A' });

  if (relatedNoteCount > 0) {
    items.push({ id: 'related-notes', label: '관련 노트', count: relatedNoteCount });
  }
  if (quoteCount > 0) {
    items.push({ id: 'quotes', label: '근거 인용', count: quoteCount });
  }

  return items;
}
