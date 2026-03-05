'use client';

import { useState } from 'react';
import { Copy, ExternalLink, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface NewsletterPreviewProps {
  html: string;
  title?: string;
}

export default function NewsletterPreview({ html, title }: NewsletterPreviewProps) {
  const [copied, setCopied] = useState(false);

  if (!html) return null;

  async function handleCopyHtml() {
    try {
      await navigator.clipboard.writeText(html);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // 폴백: textarea 복사
      const ta = document.createElement('textarea');
      ta.value = html;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  function handleOpenPreview() {
    const win = window.open('', '_blank');
    if (win) {
      win.document.write(html);
      win.document.close();
    }
  }

  return (
    <div className="mt-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-foreground/80">
          뉴스레터 미리보기
        </h4>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            className="gap-1 text-xs"
            onClick={handleCopyHtml}
          >
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            {copied ? '복사됨' : 'HTML 복사'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1 text-xs"
            onClick={handleOpenPreview}
          >
            <ExternalLink className="h-3 w-3" />
            새 탭 미리보기
          </Button>
        </div>
      </div>

      {/* 인라인 프레임 미리보기 */}
      <div className="rounded-lg border border-border/50 overflow-hidden bg-white">
        <iframe
          srcDoc={html}
          title={title ?? '뉴스레터 미리보기'}
          className="w-full h-[400px] border-0"
          sandbox="allow-same-origin"
        />
      </div>
    </div>
  );
}
