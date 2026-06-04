'use client';

import { Badge } from '@/components/ui/badge';
import { STUDIO_STEPS } from './studioConfig';

interface StudioHeroProps {
  modelLabel: string;
  resultCount: number;
}

export default function StudioHero({ modelLabel, resultCount }: StudioHeroProps) {
  const resolvedModelLabel = modelLabel || '자동 선택';
  const statusLabel = `스튜디오 상태: 선택 모델 ${resolvedModelLabel}, 생성 결과 ${resultCount}개`;

  return (
    <section
      data-testid="studio-hero"
      role="region"
      aria-labelledby="studio-hero-title"
      className="overflow-hidden rounded-[28px] border border-white/70 bg-white/85 p-5 shadow-sm shadow-slate-200/70 backdrop-blur-xl sm:p-7"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <Badge className="w-fit rounded-full bg-indigo-50 px-3 py-1 text-indigo-700 hover:bg-indigo-50">AI Content Studio</Badge>
          <div>
            <h1 id="studio-hero-title" className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">소스에서 발행까지 한 번에</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">YouTube, 웹, 텍스트를 넣고 Blog+SEO, 요약, NLM 산출물, 예약 발행까지 하나의 작업실에서 처리합니다.</p>
          </div>
        </div>
        <div
          data-testid="studio-steps"
          role="list"
          aria-label="스튜디오 작업 단계"
          className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4 lg:w-[520px]"
        >
          {STUDIO_STEPS.map((step, index) => (
            <div
              key={step.id}
              data-testid="studio-step"
              role="listitem"
              aria-label={`${index + 1}. ${step.label}: ${step.description}`}
              className="rounded-2xl border border-slate-200/70 bg-slate-50/80 p-3"
            >
              <div className="mb-2 flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-[11px] font-bold text-white">{index + 1}</div>
              <p className="font-semibold text-slate-900">{step.label}</p>
              <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-slate-500">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
      <div
        data-testid="studio-hero-status"
        role="status"
        aria-live="polite"
        aria-label={statusLabel}
        className="mt-5 flex flex-wrap gap-2 text-xs text-slate-500"
      >
        <span data-testid="studio-hero-model" aria-label={`선택 모델: ${resolvedModelLabel}`} className="rounded-full bg-slate-100 px-3 py-1">
          모델: {resolvedModelLabel}
        </span>
        <span data-testid="studio-hero-results" aria-label={`생성 결과: ${resultCount}개`} className="rounded-full bg-slate-100 px-3 py-1">
          생성 결과: {resultCount}개
        </span>
      </div>
    </section>
  );
}
