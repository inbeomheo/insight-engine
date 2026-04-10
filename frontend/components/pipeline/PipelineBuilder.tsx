'use client';

import { useState, useCallback } from 'react';
import { Plus, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import PipelineNode from './PipelineNode';

/** 파이프라인 단계 정의 */
export interface PipelineStepDef {
  id: string;
  type: string;
  label: string;
  config: Record<string, string>;
}

/** 사용 가능한 단계 타입 */
const STEP_TYPES = [
  { type: 'transcript', label: '자막 추출', description: 'URL에서 자막을 추출합니다' },
  { type: 'generate', label: 'AI 생성', description: '선택한 스타일로 콘텐츠를 생성합니다' },
  { type: 'seo', label: 'SEO 최적화', description: 'SEO 메타데이터를 생성합니다' },
  { type: 'rewrite', label: '플랫폼 리라이트', description: '플랫폼별로 변환합니다' },
  { type: 'qa', label: 'QA 검증', description: '품질 게이트를 통과합니다' },
  { type: 'publish', label: '발행', description: 'MCP 플러그인으로 발행합니다' },
];

interface PipelineBuilderProps {
  onRun?: (steps: PipelineStepDef[]) => void;
}

/** 비주얼 파이프라인 빌더 (F5-03) */
export default function PipelineBuilder({ onRun }: PipelineBuilderProps) {
  const [steps, setSteps] = useState<PipelineStepDef[]>([
    { id: '1', type: 'transcript', label: '자막 추출', config: {} },
    { id: '2', type: 'generate', label: 'AI 생성', config: { style: 'blog_seo' } },
  ]);
  const [showAddMenu, setShowAddMenu] = useState(false);

  const addStep = useCallback((type: string) => {
    const stepType = STEP_TYPES.find((s) => s.type === type);
    if (!stepType) return;

    const newStep: PipelineStepDef = {
      id: String(Date.now()),
      type,
      label: stepType.label,
      config: {},
    };
    setSteps((prev) => [...prev, newStep]);
    setShowAddMenu(false);
  }, []);

  const removeStep = useCallback((id: string) => {
    setSteps((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const updateStepConfig = useCallback((id: string, config: Record<string, string>) => {
    setSteps((prev) =>
      prev.map((s) => (s.id === id ? { ...s, config: { ...s.config, ...config } } : s)),
    );
  }, []);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const moveStep = useCallback((from: number, to: number) => {
    setSteps((prev) => {
      const next = [...prev];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
  }, []);

  return (
    <div className="space-y-4">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">파이프라인 빌더</h3>
        <Button
          size="sm"
          className="h-8 gap-1.5 gradient-primary text-white"
          onClick={() => onRun?.(steps)}
          disabled={steps.length === 0}
        >
          <Play className="h-3.5 w-3.5" />
          실행
        </Button>
      </div>

      {/* 단계 목록 */}
      <div className="space-y-2">
        {steps.map((step, idx) => (
          <div key={step.id} className="flex items-start gap-2">
            {/* 순서 + 연결선 */}
            <div className="flex flex-col items-center pt-3">
              <div className="w-6 h-6 rounded-full bg-primary/10 text-primary text-[11px]
                              font-semibold flex items-center justify-center">
                {idx + 1}
              </div>
              {idx < steps.length - 1 && (
                <div className="w-px h-full min-h-[20px] bg-border/60 mt-1" />
              )}
            </div>

            {/* 노드 */}
            <div className="flex-1">
              <PipelineNode
                step={step}
                onRemove={() => removeStep(step.id)}
                onConfigChange={(config) => updateStepConfig(step.id, config)}
              />
            </div>
          </div>
        ))}
      </div>

      {/* 단계 추가 버튼 */}
      <div className="relative">
        <Button
          variant="outline"
          size="sm"
          className="w-full h-9 border-dashed text-muted-foreground/60 gap-1.5"
          onClick={() => setShowAddMenu(!showAddMenu)}
        >
          <Plus className="h-3.5 w-3.5" />
          단계 추가
        </Button>

        {showAddMenu && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-border/60
                          rounded-lg shadow-lg z-10 py-1">
            {STEP_TYPES.map((st) => (
              <button
                key={st.type}
                className="w-full px-3 py-2 text-left text-sm hover:bg-accent/50 transition-colors"
                onClick={() => addStep(st.type)}
                aria-label={`${st.label} 단계 추가`}
              >
                <div className="font-medium text-foreground">{st.label}</div>
                <div className="text-[11px] text-muted-foreground/60">{st.description}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
