'use client';

import { ArrowDown, FileText, Sparkles, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface WorkbenchEmptyStateProps {
  onFocusSource?: () => void;
}

const GUIDE_STEPS = [
  { label: '1. 소스 입력', desc: 'URL, 텍스트, 파일, 음성 중 하나를 준비하세요.', icon: FileText },
  { label: '2. 산출물 설계', desc: '스타일, 길이, 톤, 언어와 제작 모드를 고르세요.', icon: Wand2 },
  { label: '3. Generate Dock', desc: '아래 고정 버튼에서 생성 흐름을 시작하세요.', icon: Sparkles },
  { label: '4. Result Workbench', desc: '생성 후 NLM, 변환, 내보내기, 예약을 처리합니다.', icon: ArrowDown },
] as const;

export default function WorkbenchEmptyState({ onFocusSource }: WorkbenchEmptyStateProps) {
  return (
    <section
      data-testid="studio-empty-state"
      role="region"
      aria-labelledby="studio-empty-state-title"
      className="overflow-hidden rounded-[28px] border border-dashed border-indigo-200 bg-white/75 p-6 text-left shadow-sm shadow-indigo-100/60 sm:p-8"
    >
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Start Here</p>
          <h3 id="studio-empty-state-title" data-testid="studio-empty-state-title" className="mt-2 text-xl font-semibold text-slate-950">아직 결과가 없습니다</h3>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            왼쪽부터 순서대로 진행하면 입력부터 후처리까지 한 번에 이어집니다.
          </p>
          <Button data-testid="studio-empty-state-focus-source" aria-label="소스 입력으로 이동" type="button" className="mt-4 rounded-2xl" onClick={onFocusSource}>
            소스 입력으로 이동
          </Button>
        </div>

        <div data-testid="studio-empty-state-steps" role="list" aria-label="진행 단계" className="grid flex-1 gap-2 sm:grid-cols-2">
          {GUIDE_STEPS.map((step, index) => {
            const Icon = step.icon;
            return (
              <div key={step.label} data-testid={`studio-empty-state-step-${index}`} role="listitem" aria-label={`${step.label}: ${step.desc}`} className="rounded-2xl border border-slate-200 bg-slate-50/80 p-3">
                <Icon className="mb-2 h-4 w-4 text-indigo-600" />
                <p className="text-sm font-semibold text-slate-900">{step.label}</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">{step.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
