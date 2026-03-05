'use client';

import { useCallback } from 'react';
import { Copy, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface SocialCardPreviewProps {
  title: string;
  description: string;
}

/** OG 이미지 미리보기 + 복사 버튼 */
export default function SocialCardPreview({ title, description }: SocialCardPreviewProps) {
  const ogUrl = `/api/og?title=${encodeURIComponent(title)}&description=${encodeURIComponent(description)}`;

  const handleCopy = useCallback(async () => {
    try {
      const fullUrl = `${window.location.origin}${ogUrl}`;
      await navigator.clipboard.writeText(fullUrl);
      toast.success('OG 이미지 URL이 복사되었습니다.');
    } catch {
      toast.error('복사에 실패했습니다.');
    }
  }, [ogUrl]);

  return (
    <div className="mt-3 rounded-xl border border-border/50 overflow-hidden bg-muted/20">
      {/* 미리보기 이미지 */}
      <div className="aspect-[1200/630] bg-slate-900 relative">
        <img
          src={ogUrl}
          alt="소셜 카드 미리보기"
          className="w-full h-full object-cover"
          loading="lazy"
        />
      </div>

      {/* 하단 정보 */}
      <div className="px-3 py-2 flex items-center justify-between">
        <span className="text-xs text-muted-foreground truncate">OG 이미지 · 1200×630</span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCopy} title="URL 복사">
            <Copy className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7" asChild title="새 탭에서 보기">
            <a href={ogUrl} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </Button>
        </div>
      </div>
    </div>
  );
}
