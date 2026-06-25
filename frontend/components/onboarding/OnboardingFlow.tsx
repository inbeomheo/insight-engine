'use client';

import { useState } from 'react';
import { ChevronRight, Check, Image as ImageIcon } from 'lucide-react';
import { TUTORIAL_ONBOARDING_STEPS } from '@/lib/tutorialAssets';

interface OnboardingStep {
  id?: string;
  title: string;
  description: string;
  imageSrc?: string;
  imageAlt?: string;
  fallbackLabel?: string;
  action?: () => void;
}

const DEFAULT_STEPS: OnboardingStep[] = TUTORIAL_ONBOARDING_STEPS.map((step) => ({
  id: step.id,
  title: step.title,
  description: step.description,
  imageSrc: step.imageSrc,
  imageAlt: step.imageAlt,
  fallbackLabel: step.fallbackLabel,
}));

interface OnboardingFlowProps {
  steps?: OnboardingStep[];
  onComplete?: () => void;
}

/** 신규 사용자 온보딩 플로우 (F4-19) */
export default function OnboardingFlow({ steps = DEFAULT_STEPS, onComplete }: OnboardingFlowProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [completed, setCompleted] = useState(false);
  const [brokenImages, setBrokenImages] = useState<Record<string, boolean>>({});
  const visibleSteps = steps.length > 0 ? steps : DEFAULT_STEPS;
  const currentIndex = Math.min(currentStep, visibleSteps.length - 1);
  const step = visibleSteps[currentIndex];
  const stepKey = step.id ?? String(currentIndex);

  const handleNext = () => {
    step.action?.();

    if (currentIndex < visibleSteps.length - 1) {
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
        {visibleSteps.map((_, idx) => (
          <div
            key={idx}
            className={`h-1.5 flex-1 rounded-full ${
              idx <= currentIndex ? 'bg-indigo-500' : 'bg-white/10'
            }`}
          />
        ))}
      </div>

      {step.imageSrc && !brokenImages[stepKey] ? (
        <img
          src={step.imageSrc}
          alt={step.imageAlt ?? step.title}
          loading="lazy"
          className="aspect-[16/10] w-full rounded-lg border border-white/10 object-cover"
          onError={() => setBrokenImages((prev) => ({ ...prev, [stepKey]: true }))}
        />
      ) : (
        <div className="flex aspect-[16/10] flex-col items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 text-center">
          <ImageIcon className="h-6 w-6 text-gray-500" />
          <p className="text-sm font-semibold">{step.fallbackLabel ?? step.title}</p>
          <p className="text-xs leading-5 text-gray-400">{step.description}</p>
        </div>
      )}

      {/* 현재 스텝 */}
      <div className="space-y-2">
        <p className="text-xs text-gray-400">
          단계 {currentIndex + 1} / {visibleSteps.length}
        </p>
        <h3 className="text-lg font-semibold">{step.title}</h3>
        <p className="text-sm text-gray-400">{step.description}</p>
      </div>

      <button
        onClick={handleNext}
        aria-label={currentIndex < visibleSteps.length - 1 ? '다음 단계' : '온보딩 완료'}
        className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-500"
      >
        {currentIndex < visibleSteps.length - 1 ? '다음' : '완료'}
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
