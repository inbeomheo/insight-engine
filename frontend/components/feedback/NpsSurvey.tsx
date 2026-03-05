'use client';

import { useState } from 'react';
import { Send, Check } from 'lucide-react';

interface NpsSurveyProps {
  onSubmit?: (score: number, feedback: string) => Promise<void>;
}

/** NPS 설문조사 컴포넌트 (F4-20) */
export default function NpsSurvey({ onSubmit }: NpsSurveyProps) {
  const [score, setScore] = useState<number | null>(null);
  const [feedback, setFeedback] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (score === null) return;
    setLoading(true);
    try {
      if (onSubmit) {
        await onSubmit(score, feedback);
      } else {
        await fetch('/api/feedback/nps', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ score, feedback }),
        });
      }
      setSubmitted(true);
    } catch {
      // 실패 시 무시
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-green-400">
        <Check className="h-4 w-4" />
        소중한 피드백 감사합니다!
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-xl border border-white/10 bg-white/5 p-5">
      <p className="text-sm font-medium">
        이 서비스를 친구/동료에게 추천할 의향이 있으신가요?
      </p>

      {/* 0-10 점수 선택 */}
      <div className="flex gap-1">
        {Array.from({ length: 11 }, (_, i) => (
          <button
            key={i}
            onClick={() => setScore(i)}
            className={`flex h-9 w-9 items-center justify-center rounded-lg text-sm font-medium transition-colors ${
              score === i
                ? 'bg-indigo-600 text-white'
                : 'bg-white/5 text-gray-400 hover:bg-white/10'
            }`}
          >
            {i}
          </button>
        ))}
      </div>
      <div className="flex justify-between text-xs text-gray-500">
        <span>전혀 아니다</span>
        <span>매우 그렇다</span>
      </div>

      {/* 텍스트 피드백 */}
      {score !== null && (
        <>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="개선사항이나 좋았던 점을 알려주세요 (선택)"
            rows={2}
            className="w-full rounded-lg border border-white/10 bg-white/5 p-3 text-sm placeholder:text-gray-500 focus:border-indigo-500 focus:outline-none"
          />
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            제출
          </button>
        </>
      )}
    </div>
  );
}
