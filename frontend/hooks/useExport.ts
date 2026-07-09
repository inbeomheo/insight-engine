'use client';

import { useCallback } from 'react';
import { EXPORT_HTML_STYLE } from '@/lib/exportHtmlTemplate';
import { toast } from 'sonner';
import type { Report } from '@/lib/types';

/** script 태그 및 이벤트 핸들러 속성 제거 */
function sanitizeHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<script[^>]*>/gi, '')
    .replace(/\s+on\w+\s*=\s*["'][^"']*["']/gi, '')
    .replace(/\s+on\w+\s*=\s*\S+/gi, '');
}

/** Blob을 파일로 다운로드시키고 성공 토스트 표시 */
function triggerDownload(blob: Blob, filename: string, successMsg: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  toast.success(successMsg);
}

export function useExport() {
  const downloadHtml = useCallback((report: Report) => {
    try {
      const html = `<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>${report.title}</title>
<style>${EXPORT_HTML_STYLE}</style></head><body>${sanitizeHtml(report.html || report.content)}</body></html>`;
      const blob = new Blob([html], { type: 'text/html' });
      triggerDownload(blob, `${report.title.slice(0, 50)}.html`, 'HTML 다운로드 완료');
    } catch {
      toast.error('HTML 내보내기에 실패했습니다');
    }
  }, []);

  const downloadMarkdown = useCallback((report: Report) => {
    try {
      const blob = new Blob([report.content], { type: 'text/markdown' });
      triggerDownload(blob, `${report.title.slice(0, 50)}.md`, '마크다운 다운로드 완료');
    } catch {
      toast.error('마크다운 내보내기에 실패했습니다');
    }
  }, []);

  return { downloadHtml, downloadMarkdown };
}
