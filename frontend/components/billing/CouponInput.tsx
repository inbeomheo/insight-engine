'use client';

import { useState } from 'react';
import { Tag, Check, Loader2 } from 'lucide-react';

interface CouponInputProps {
  onApply: (code: string) => Promise<{ discount?: number; error?: string }>;
}

/** 쿠폰 코드 입력 + 검증 컴포넌트 (F4-12) */
export default function CouponInput({ onApply }: CouponInputProps) {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ discount?: number; error?: string } | null>(null);

  const handleApply = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await onApply(code.trim());
      setResult(res);
    } catch {
      setResult({ error: '쿠폰 적용 중 오류가 발생했습니다.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Tag className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500 dark:text-gray-400" />
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="쿠폰 코드 입력"
            className="w-full rounded-lg border border-white/10 bg-white/5 py-2 pl-10 pr-3 text-sm placeholder:text-gray-500 focus:border-indigo-500 focus:outline-none"
            onKeyDown={(e) => e.key === 'Enter' && handleApply()}
          />
        </div>
        <button
          onClick={handleApply}
          disabled={loading || !code.trim()}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          aria-label="쿠폰 적용"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : '적용'}
        </button>
      </div>

      {result && (
        <p className={`text-sm ${result.error ? 'text-red-400' : 'text-green-400'}`}>
          {result.error
            ? result.error
            : <>
                <Check className="mr-1 inline h-4 w-4" />
                {result.discount?.toLocaleString()}원 할인 적용됨
              </>
          }
        </p>
      )}
    </div>
  );
}
