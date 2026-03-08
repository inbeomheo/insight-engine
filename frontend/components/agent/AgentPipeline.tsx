'use client';

import { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { apiUrl } from '@/lib/api';
import AgentProgress from './AgentProgress';

interface PipelineResult {
  pipeline_results: Array<{
    agent: string;
    result: Record<string, unknown>;
  }>;
  final: {
    title: string;
    content: string;
    seo: Record<string, unknown>;
    sources: Array<{ title: string; url: string; summary: string }>;
  };
  elapsed_seconds: number;
  agent_count: number;
}

interface AgentPipelineProps {
  onComplete?: (result: PipelineResult) => void;
  className?: string;
}

const AGENT_STEPS = [
  { id: 'research', name: '리서처', description: '웹 검색 및 자료 수집' },
  { id: 'writer', name: '작가', description: '초안 작성' },
  { id: 'editor', name: '편집자', description: '문법/흐름 개선' },
  { id: 'seo', name: 'SEO', description: '메타데이터 최적화' },
];

export default function AgentPipeline({ onComplete, className }: AgentPipelineProps) {
  const [topic, setTopic] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<Array<{
    phase: string;
    message: string;
    data: Record<string, unknown>;
    iteration: number;
    progress: number;
    timestamp: number;
  }>>([]);
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [error, setError] = useState('');
  const [currentStep, setCurrentStep] = useState(-1);

  const runPipeline = useCallback(async () => {
    if (!topic.trim() || isRunning) return;

    setIsRunning(true);
    setEvents([]);
    setResult(null);
    setError('');
    setCurrentStep(0);

    try {
      const res = await fetch(apiUrl('/api/agent/pipeline'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic.trim() }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || '파이프라인 실행 실패');
      }

      const data: PipelineResult = await res.json();
      setResult(data);
      setCurrentStep(AGENT_STEPS.length);
      onComplete?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류');
    } finally {
      setIsRunning(false);
    }
  }, [topic, isRunning, onComplete]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* 입력 */}
      <div className="flex gap-2">
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="콘텐츠 주제를 입력하세요..."
          className="flex-1 rounded-md border px-3 py-2 text-sm"
          disabled={isRunning}
          onKeyDown={(e) => e.key === 'Enter' && runPipeline()}
        />
        <button
          onClick={runPipeline}
          disabled={!topic.trim() || isRunning}
          className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
          aria-label="에이전트 파이프라인 실행"
        >
          {isRunning ? '실행 중...' : '파이프라인 실행'}
        </button>
      </div>

      {/* 단계 표시 */}
      <div className="flex gap-1">
        {AGENT_STEPS.map((step, idx) => (
          <div
            key={step.id}
            className={cn(
              'flex-1 rounded-md p-2 text-center text-xs transition-colors',
              idx < currentStep && 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
              idx === currentStep && isRunning && 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 animate-pulse',
              idx > currentStep && 'bg-muted text-muted-foreground',
            )}
          >
            <div className="font-medium">{step.name}</div>
            <div className="opacity-70">{step.description}</div>
          </div>
        ))}
      </div>

      {/* 진행 상황 */}
      <AgentProgress events={events} isRunning={isRunning} />

      {/* 에러 */}
      {error && (
        <div className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {/* 결과 */}
      {result && (
        <div className="space-y-3 rounded-lg border p-4">
          <div className="flex items-center justify-between">
            <h3 className="font-medium">{result.final.title || '생성된 콘텐츠'}</h3>
            <span className="text-xs text-muted-foreground">
              {result.elapsed_seconds}초 / {result.agent_count}개 에이전트
            </span>
          </div>

          {result.final.sources.length > 0 && (
            <div className="text-xs text-muted-foreground">
              참고 소스: {result.final.sources.map((s) => s.title).join(', ')}
            </div>
          )}

          <div className="prose prose-sm dark:prose-invert max-h-96 overflow-y-auto whitespace-pre-wrap">
            {result.final.content}
          </div>
        </div>
      )}
    </div>
  );
}
