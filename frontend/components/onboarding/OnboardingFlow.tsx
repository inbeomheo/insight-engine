'use client';

import { useState } from 'react';
import { ChevronRight, Check } from 'lucide-react';

interface OnboardingStep {
  title: string;
  description: string;
  action?: () => void;
}

const DEFAULT_STEPS: OnboardingStep[] = [
  { title: 'ChatMock 실행', description: '터미널에서 chatmock login 후 chatmock serve를 실행하세요.' },
  { title: '첫 학습 노트 생성', description: 'YouTube URL, 문서, 텍스트 중 하나를 넣고 스타일을 선택하세요.' },
  { title: '지식으로 쌓기', description: '생성된 노트를 확인하고 Markdown 또는 HTML로 내보내세요.' },
];

interface OnboardingFlowProps {
  steps?: OnboardingStep[];
  onComplete?: () => void;
}

/** 신규 사용자 온보딩 플로우 (F4-19) */
export default function OnboardingFlow({ steps = DEFAULT_STEPS, onComplete }: OnboardingFlowProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [completed, setCompleted] = useState(false);

  const handleNext = () => {
    const step = steps[currentStep];
    step.action?.();

    if (currentStep < steps.length - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      setCompleted(true);
      onComplete?.();
    }
  };

  if (completed) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-500/20">
          <Check className="h-6 w-6 text-green-400" />
        </div>
        <h3 className="text-lg font-semibold">설정 완료!</h3>
        <p className="text-sm text-gray-400">이제 콘텐츠를 생성해보세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 rounded-xl border border-white/10 bg-white/5 p-6">
      {/* 진행 바 */}
      <div className="flex gap-2">
        {steps.map((_, idx) => (
          <div
            key={idx}
            className={`h-1.5 flex-1 rounded-full ${
              idx <= currentStep ? 'bg-indigo-500' : 'bg-white/10'
            }`}
          />
        ))}
      </div>

      {/* 현재 스텝 */}
      <div className="space-y-2">
        <p className="text-xs text-gray-400">
          단계 {currentStep + 1} / {steps.length}
        </p>
        <h3 className="text-lg font-semibold">{steps[currentStep].title}</h3>
        <p className="text-sm text-gray-400">{steps[currentStep].description}</p>
      </div>

      <button
        onClick={handleNext}
        aria-label={currentStep < steps.length - 1 ? '다음 단계' : '온보딩 완료'}
        className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-500"
      >
        {currentStep < steps.length - 1 ? '다음' : '완료'}
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
