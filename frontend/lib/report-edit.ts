// 생성된 문서(리포트) 직접 편집 — 초안 정규화/검증 순수 함수
// 저장 자체는 resultStore.updateReport(=localStorage)로 처리한다.
import type { Report } from '@/lib/types';

export interface ReportDraft {
  title: string;
  content: string;
}

export type ReportDraftError = 'emptyTitle' | 'emptyContent';

/** 편집 초안 정규화 — 제목은 앞뒤 공백 제거, 본문은 끝 공백만 제거(들여쓰기 보존) */
export function normalizeReportDraft(draft: ReportDraft): ReportDraft {
  return {
    title: draft.title.trim(),
    content: draft.content.replace(/\s+$/, ''),
  };
}

/** 저장 가능 여부 검증 — 문제가 없으면 null */
export function validateReportDraft(draft: ReportDraft): ReportDraftError | null {
  const normalized = normalizeReportDraft(draft);
  if (!normalized.title) return 'emptyTitle';
  if (!normalized.content) return 'emptyContent';
  return null;
}

/** 정규화 후 실제 변경이 있는지 (없으면 저장/재렌더 생략) */
export function hasReportChanges(
  report: Pick<Report, 'title' | 'content'>,
  draft: ReportDraft,
): boolean {
  const normalized = normalizeReportDraft(draft);
  return normalized.title !== report.title || normalized.content !== report.content;
}
