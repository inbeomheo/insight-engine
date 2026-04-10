'use client';

import { useState, useEffect } from 'react';

interface FusionProgressProps {
  isLoading: boolean;
  isFusion: boolean;
}

const steps = [
  { label: '자막 수집 중...', duration: 5000 },
  { label: '댓글 분석 중...', duration: 8000 },
  { label: '웹 리서치 중...', duration: 10000 },
  { label: '최종 글 생성 중...', duration: 15000 },
];

export default function FusionProgress({ isLoading, isFusion }: FusionProgressProps) {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (!isLoading) { setCurrentStep(0); return; }
    const timers = steps.map((_, i) =>
      setTimeout(() => setCurrentStep(i),
        steps.slice(0, i).reduce((a, s) => a + s.duration, 0))
    );
    return () => timers.forEach(clearTimeout);
  }, [isLoading]);

  if (!isLoading || !isFusion) return null;

  return (
    <div className="my-4 rounded-lg border border-[var(--border-primary)] p-4">
      <p className="mb-3 text-sm font-medium">퓨전 분석 진행 중...</p>
      <div className="space-y-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span className={i <= currentStep ? 'text-green-400' : 'text-[var(--text-tertiary)]'}>
              {i < currentStep ? '\u2713' : i === currentStep ? '\u25CF' : '\u25CB'}
            </span>
            <span className={i <= currentStep ? 'text-[var(--text-primary)]' : 'text-[var(--text-tertiary)]'}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
