'use client';

import { memo, useEffect, useState } from 'react';
import { Gift, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';

interface ReferralInfo {
  code: string;
  referral_count: number;
  total_earned: number;
}

export const ReferralCard = memo(function ReferralCard() {
  const [info, setInfo] = useState<ReferralInfo | null>(null);
  const [copied, setCopied] = useState(false);
  const [applyCode, setApplyCode] = useState('');
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    fetch('/api/referral/info')
      .then((r) => (r.ok ? r.json() : null))
      .then(setInfo)
      .catch(() => {});
  }, []);

  const handleCopy = async () => {
    if (!info) return;
    await navigator.clipboard.writeText(info.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApply = async () => {
    if (!applyCode.trim()) {
      toast.error('추천 코드를 입력해주세요.');
      return;
    }
    setApplying(true);
    try {
      const res = await fetch('/api/referral/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: applyCode.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        toast.success(`추천 보상 ${data.credits_given} 크레딧이 지급되었습니다!`);
        setApplyCode('');
      } else {
        toast.error(data.error || '추천 코드 적용 실패');
      }
    } catch {
      toast.error('요청 중 오류가 발생했습니다.');
    } finally {
      setApplying(false);
    }
  };

  if (!info) return null;

  return (
    <div className="rounded-lg border p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Gift className="h-5 w-5 text-pink-500" />
        <h3 className="font-semibold">친구 추천</h3>
      </div>

      {/* 내 추천 코드 */}
      <div>
        <p className="text-sm text-muted-foreground mb-1">내 추천 코드</p>
        <div className="flex items-center gap-2">
          <code className="flex-1 rounded bg-muted px-3 py-1.5 text-sm font-mono">
            {info.code}
          </code>
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {/* 통계 */}
      <div className="flex gap-4 text-sm">
        <div>
          <span className="text-muted-foreground">추천 수:</span>{' '}
          <strong>{info.referral_count}</strong>
        </div>
        <div>
          <span className="text-muted-foreground">총 적립:</span>{' '}
          <strong>{info.total_earned} 크레딧</strong>
        </div>
      </div>

      {/* 추천 코드 입력 */}
      <div>
        <p className="text-sm text-muted-foreground mb-1">추천 코드 입력</p>
        <div className="flex gap-2">
          <Input
            placeholder="친구의 추천 코드"
            value={applyCode}
            onChange={(e) => setApplyCode(e.target.value)}
          />
          <Button onClick={handleApply} disabled={applying} size="sm">
            {applying ? '적용 중...' : '적용'}
          </Button>
        </div>
      </div>
    </div>
  );
});
