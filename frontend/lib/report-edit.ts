// 생성된 문서(리포트) 직접 편집 — 초안 정규화/검증 순수 함수
// 저장 자체는 resultStore.updateReportPersisted(=localStorage)로 처리한다.
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

/** HTML 텍스트 컨텍스트(<title> 등)에 안전하게 삽입할 수 있도록 이스케이프한다. */
export function escapeHtmlText(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/** 사용자 제목에서 제어문자와 경로/파일시스템 예약문자를 제거한 다운로드 파일명 생성. */
export function createDownloadFilename(title: string, extension: 'html' | 'md'): string {
  const base = title
    .replace(/[\u0000-\u001f\u007f-\u009f/\\:*?"<>|]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^[. ]+|[. ]+$/g, '')
    .slice(0, 50)
    .replace(/[. ]+$/g, '');
  return `${base || 'report'}.${extension}`;
}

/** NotebookLM API 상태를 UI가 지원하는 종료 상태로 정규화한다. */
export function getNotebookLmTerminalStatus(status: string): 'completed' | 'failed' | null {
  if (status === 'completed') return 'completed';
  if (status === 'failed' || status === 'not_found') return 'failed';
  return null;
}
