'use client';

import { useCallback } from 'react';
import { exportDocx } from '@/lib/api';
import { EXPORT_HTML_STYLE, PRINT_HTML_STYLE } from '@/lib/exportHtmlTemplate';
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

export function useExport() {
  const downloadDocx = useCallback(async (report: Report) => {
    try {
      const blob = await exportDocx(report.title, report.content);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.slice(0, 50)}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('DOCX 다운로드 완료');
    } catch {
      toast.error('DOCX 내보내기 실패');
    }
  }, []);

  const downloadHtml = useCallback((report: Report) => {
    try {
      const html = `<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>${report.title}</title>
<style>${EXPORT_HTML_STYLE}</style></head><body>${sanitizeHtml(report.html || report.content)}</body></html>`;
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.slice(0, 50)}.html`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('HTML 다운로드 완료');
    } catch {
      toast.error('HTML 내보내기에 실패했습니다');
    }
  }, []);

  const downloadMarkdown = useCallback((report: Report) => {
    try {
      const blob = new Blob([report.content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.slice(0, 50)}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('마크다운 다운로드 완료');
    } catch {
      toast.error('마크다운 내보내기에 실패했습니다');
    }
  }, []);

  const printPdf = useCallback((report: Report) => {
    const w = window.open('', '_blank');
    if (!w) {
      toast.error('팝업이 차단되었습니다. 브라우저 설정에서 팝업을 허용해주세요.');
      return;
    }
    w.document.write(`<!DOCTYPE html>
<html><head><title>${report.title}</title>
<style>${PRINT_HTML_STYLE}</style></head>
<body>${sanitizeHtml(report.html || report.content)}</body></html>`);
    w.document.close();
    w.print();
  }, []);

  return { downloadDocx, downloadHtml, downloadMarkdown, printPdf };
}
