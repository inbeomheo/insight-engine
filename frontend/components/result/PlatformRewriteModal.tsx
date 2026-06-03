'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Copy, Check, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { rewriteForPlatform } from '@/lib/api';
import { useSettingsStore } from '@/stores/settingsStore';

const PLATFORMS = [
  { id: 'twitter', label: 'Twitter / X', maxChars: 280, emoji: '🐦' },
  { id: 'linkedin', label: 'LinkedIn', maxChars: 3000, emoji: '💼' },
  { id: 'instagram', label: 'Instagram', maxChars: 2200, emoji: '📸' },
  { id: 'threads', label: 'Threads', maxChars: 500, emoji: '🧵' },
] as const;

interface PlatformRewriteModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  content: string;
}

export default function PlatformRewriteModal({ open, onOpenChange, content }: PlatformRewriteModalProps) {
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [charCount, setCharCount] = useState(0);
  const [maxChars, setMaxChars] = useState(0);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const selectedModel = useSettingsStore((s) => s.selectedModel);

  async function handleRewrite(platformId: string) {
    setSelectedPlatform(platformId);
    setResult(null);
    setLoading(true);

    try {
      const res = await rewriteForPlatform(content, platformId, selectedModel || undefined);
      setResult(res.text);
      setCharCount(res.char_count);
      setMaxChars(res.max_chars);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '변환에 실패했습니다.');
      setSelectedPlatform(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy() {
    if (!result) return;
    await navigator.clipboard.writeText(result);
    setCopied(true);
    toast.success('복사되었습니다');
    setTimeout(() => setCopied(false), 2000);
  }

  function handleClose(v: boolean) {
    if (!v) {
      setSelectedPlatform(null);
      setResult(null);
      setCopied(false);
    }
    onOpenChange(v);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>플랫폼별 카피 변환</DialogTitle>
          <DialogDescription>콘텐츠를 SNS 플랫폼에 맞게 변환합니다.</DialogDescription>
        </DialogHeader>

        {/* 플랫폼 선택 */}
        <div
          data-testid="platform-rewrite-options"
          role="radiogroup"
          aria-label="변환 플랫폼"
          className="grid grid-cols-2 gap-2"
        >
          {PLATFORMS.map((p) => (
            <Button
              key={p.id}
              data-testid={`platform-rewrite-${p.id}`}
              role="radio"
              aria-checked={selectedPlatform === p.id}
              aria-label={`${p.label} 변환`}
              variant={selectedPlatform === p.id ? 'default' : 'outline'}
              className="justify-start gap-2 h-auto py-3"
              onClick={() => handleRewrite(p.id)}
              disabled={loading}
            >
              <span className="text-lg">{p.emoji}</span>
              <div className="text-left">
                <div className="text-sm font-medium">{p.label}</div>
                <div className="text-[10px] text-muted-foreground">최대 {p.maxChars.toLocaleString()}자</div>
              </div>
            </Button>
          ))}
        </div>

        {/* 결과 영역 */}
        {loading && (
          <div
            data-testid="platform-rewrite-loading"
            role="status"
            aria-live="polite"
            className="flex items-center justify-center py-8 text-sm text-muted-foreground"
          >
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            변환 중...
          </div>
        )}

        {result && !loading && (
          <div
            data-testid="platform-rewrite-result"
            role="region"
            aria-live="polite"
            aria-label="플랫폼 변환 결과"
            className="space-y-3 pt-2"
          >
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="text-xs">
                {charCount.toLocaleString()} / {maxChars.toLocaleString()}자
              </Badge>
              <Button
                data-testid="platform-rewrite-copy"
                aria-label="변환 결과 복사"
                variant="ghost"
                size="sm"
                className="h-7 text-xs gap-1.5"
                onClick={handleCopy}
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
                {copied ? '복사됨' : '복사'}
              </Button>
            </div>

            <div className="rounded-lg border bg-muted/30 p-4 text-sm leading-relaxed whitespace-pre-wrap">
              {result}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
