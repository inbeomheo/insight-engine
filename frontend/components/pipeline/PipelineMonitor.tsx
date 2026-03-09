/**
 * 콘텐츠 파이프라인 모니터 컴포넌트 (F10-28)
 * 실시간 파이프라인 진행 상황 시각화
 * SSE 스트리밍으로 단계별 상태 업데이트
 */
'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { apiUrl } from '@/lib/api';

// ── 타입 정의 ─────────────────────────────────────────────────────────────────

type StepStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

interface PipelineStep {
  step_id: string;
  name: string;
  status: StepStatus;
  message?: string;
  progress?: number;   // 0~100
  duration_ms?: number;
  started_at?: number;
  completed_at?: number;
}

interface PipelineState {
  pipeline_id: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  steps: PipelineStep[];
  overall_progress: number;
  started_at?: number;
  completed_at?: number;
  result?: Record<string, unknown>;
  error?: string;
}

// ── 상수 ──────────────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<StepStatus, { bg: string; text: string; icon: string }> = {
  pending:  { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-500', icon: '○' },
  running:  { bg: 'bg-blue-50 dark:bg-blue-900/30', text: 'text-blue-600 dark:text-blue-400', icon: '◉' },
  success:  { bg: 'bg-green-50 dark:bg-green-900/30', text: 'text-green-600 dark:text-green-400', icon: '✓' },
  failed:   { bg: 'bg-red-50 dark:bg-red-900/30', text: 'text-red-600 dark:text-red-400', icon: '✗' },
  skipped:  { bg: 'bg-gray-50 dark:bg-gray-800/50', text: 'text-gray-400', icon: '−' },
};

// ── 단일 스텝 컴포넌트 ────────────────────────────────────────────────────────

function StepCard({ step }: { step: PipelineStep }) {
  const style = STATUS_STYLES[step.status];
  const duration = step.duration_ms
    ? step.duration_ms < 1000
      ? `${step.duration_ms}ms`
      : `${(step.duration_ms / 1000).toFixed(1)}s`
    : null;

  return (
    <div className={`rounded-lg p-3 border border-transparent transition-colors ${style.bg}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`font-mono text-sm font-bold ${style.text}`}>
            {step.status === 'running' ? (
              <span className="animate-pulse">{style.icon}</span>
            ) : style.icon}
          </span>
          <span className={`text-sm font-medium ${style.text}`}>{step.name}</span>
        </div>
        {duration && (
          <span className="text-xs text-gray-400 dark:text-gray-500">{duration}</span>
        )}
      </div>

      {/* 진행 바 (running 상태) */}
      {step.status === 'running' && step.progress !== undefined && (
        <div className="mt-2 h-1 bg-blue-100 dark:bg-blue-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${step.progress}%` }}
          />
        </div>
      )}

      {/* 메시지 */}
      {step.message && (
        <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400 truncate">
          {step.message}
        </p>
      )}
    </div>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────────────────────

interface PipelineMonitorProps {
  pipelineId?: string;
  onComplete?: (result: Record<string, unknown>) => void;
  onError?: (error: string) => void;
  className?: string;
}

export function PipelineMonitor({
  pipelineId,
  onComplete,
  onError,
  className = '',
}: PipelineMonitorProps) {
  const [state, setState] = useState<PipelineState>({
    pipeline_id: pipelineId || '',
    status: 'idle',
    steps: [],
    overall_progress: 0,
  });
  const eventSourceRef = useRef<EventSource | null>(null);

  const connectSSE = useCallback((id: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const es = new EventSource(apiUrl(`/api/pipeline/${id}/stream`));
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Partial<PipelineState>;
        setState(prev => ({
          ...prev,
          ...data,
          steps: data.steps || prev.steps,
        }));

        if (data.status === 'completed' && data.result) {
          onComplete?.(data.result);
          es.close();
        } else if (data.status === 'failed') {
          onError?.(data.error || '파이프라인 실패');
          es.close();
        }
      } catch {
        // JSON 파싱 오류 무시
      }
    };

    es.onerror = () => {
      es.close();
      setState(prev => ({
        ...prev,
        status: prev.status === 'running' ? 'failed' : prev.status,
      }));
    };
  }, [onComplete, onError]);

  useEffect(() => {
    if (pipelineId) {
      connectSSE(pipelineId);
    }
    return () => {
      eventSourceRef.current?.close();
    };
  }, [pipelineId, connectSSE]);

  const successCount = state.steps.filter(s => s.status === 'success').length;
  const totalCount = state.steps.filter(s => s.status !== 'skipped').length;

  return (
    <div className={`space-y-3 ${className}`}>
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white">
            파이프라인 모니터
          </h3>
          {state.status !== 'idle' && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              state.status === 'running' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 animate-pulse' :
              state.status === 'completed' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' :
              state.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' :
              'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
            }`}>
              {state.status === 'running' ? '실행 중' :
               state.status === 'completed' ? '완료' :
               state.status === 'failed' ? '실패' : state.status}
            </span>
          )}
        </div>
        {totalCount > 0 && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {successCount}/{totalCount}
          </span>
        )}
      </div>

      {/* 전체 진행 바 */}
      {state.status !== 'idle' && (
        <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              state.status === 'failed' ? 'bg-red-500' :
              state.status === 'completed' ? 'bg-green-500' :
              'bg-blue-500'
            }`}
            style={{ width: `${state.overall_progress}%` }}
          />
        </div>
      )}

      {/* 스텝 목록 */}
      {state.steps.length > 0 ? (
        <div className="space-y-2">
          {state.steps.map(step => (
            <StepCard key={step.step_id} step={step} />
          ))}
        </div>
      ) : (
        <div className="flex items-center justify-center h-24 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <p className="text-sm text-gray-400 dark:text-gray-500">
            {pipelineId ? '파이프라인 연결 중…' : '파이프라인을 시작하세요'}
          </p>
        </div>
      )}

      {/* 오류 메시지 */}
      {state.error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3">
          <p className="text-xs text-red-600 dark:text-red-400">{state.error}</p>
        </div>
      )}
    </div>
  );
}

// ── 인라인 미니 버전 ──────────────────────────────────────────────────────────

export function PipelineProgressBar({
  progress,
  status,
  stepName,
}: {
  progress: number;
  status: PipelineState['status'];
  stepName?: string;
}) {
  return (
    <div className="space-y-1">
      {stepName && (
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{stepName}</p>
      )}
      <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            status === 'failed' ? 'bg-red-500' :
            status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
