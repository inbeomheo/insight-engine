'use client';

import { useState } from 'react';
import type {
  FusionMeta,
  FusionPipelineStep,
  FusionPipelineStepStatus,
  FusionPipelineTrace,
  FusionQualityStatus,
  FusionQualitySummary,
  FusionSections as FusionSectionsType,
} from '@/lib/types';
import QualitySummaryPanel from './QualitySummaryPanel';

interface FusionSectionsProps {
  sections?: FusionSectionsType;
  fusionMeta?: FusionMeta;
  pipelineTrace?: FusionPipelineTrace;
  qualitySummary?: FusionQualitySummary;
}

const STEP_LABELS: Record<string, string> = {
  transcript_collect: '자막 수집',
  transcript_summarize: '자막 요약',
  comment_collect: '댓글 수집',
  comment_analyze: '댓글 분석',
  web_research: '웹 리서치',
  final_generation: '최종 생성',
};

const TRACE_LABELS: Record<FusionPipelineStepStatus, string> = {
  success: '완료',
  warning: '주의',
  error: '오류',
};

function statusClass(status?: FusionQualityStatus | FusionPipelineStepStatus): string {
  if (status === 'warning') return 'border-yellow-500/30 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400';
  if (status === 'error') return 'border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400';
  if (status === 'disabled') return 'border-border bg-muted/40 text-muted-foreground';
  return 'border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400';
}

function traceLabel(step: FusionPipelineStep): string {
  if (step.enabled === false) return '꺼짐';
  return TRACE_LABELS[step.status] ?? step.status;
}

function stepDetail(step: FusionPipelineStep): string {
  const parts = [
    step.requested_count !== undefined ? `요청 ${step.requested_count}개` : null,
    step.count !== undefined ? `결과 ${step.count}개` : null,
    step.collected_count !== undefined ? `수집 ${step.collected_count}개` : null,
    step.analyzed_count !== undefined ? `반영 ${step.analyzed_count}개` : null,
    step.sources_found !== undefined ? `소스 ${step.sources_found}개` : null,
    step.failed_count ? `실패 ${step.failed_count}개` : null,
  ].filter(Boolean);
  return parts.join(' · ');
}

export default function FusionSections({ sections, fusionMeta, pipelineTrace, qualitySummary }: FusionSectionsProps) {
  const [faqOpen, setFaqOpen] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  const faq = sections?.faq ?? '';
  const factChecks = sections?.fact_checks ?? [];
  const sourcesUsed = sections?.sources_used ?? [];
  const traceSteps = pipelineTrace?.steps ?? [];
  const warnings = qualitySummary?.warnings?.length ? qualitySummary.warnings : (pipelineTrace?.warnings ?? []);

  if (!sections && !fusionMeta && !pipelineTrace && !qualitySummary) return null;

  return (
    <div className="mt-4 space-y-3">
      {fusionMeta && (
        <div className="flex flex-wrap gap-2 text-xs">
          <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-blue-400">
            영상 {fusionMeta.videos_analyzed ?? 0}개
          </span>
          {(fusionMeta.comments_analyzed ?? 0) > 0 && (
            <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-green-400">
              댓글 {fusionMeta.comments_analyzed}개
            </span>
          )}
          {(fusionMeta.web_sources_found ?? 0) > 0 && (
            <span className="rounded-full bg-purple-500/10 px-2 py-0.5 text-purple-400">
              외부소스 {fusionMeta.web_sources_found}개
            </span>
          )}
        </div>
      )}

      {qualitySummary && (
        <QualitySummaryPanel
          summary={qualitySummary}
          model={pipelineTrace?.model}
          warnings={warnings}
        />
      )}

      {traceSteps.length > 0 && (
        <details className="rounded-md border border-border/70 bg-background/50">
          <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-foreground">
            실행 단계 ({traceSteps.length}개)
          </summary>
          <div className="space-y-2 border-t border-border/60 p-3">
            {traceSteps.map((step, i) => (
              <div key={`${step.name}-${i}`} className="flex flex-col gap-1 rounded-md bg-muted/20 px-3 py-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-medium text-foreground">{STEP_LABELS[step.name] ?? step.name}</p>
                  {stepDetail(step) && (
                    <p className="break-words text-xs leading-5 text-muted-foreground">{stepDetail(step)}</p>
                  )}
                </div>
                <span className={`w-fit shrink-0 rounded-full border px-2 py-0.5 text-[10px] ${statusClass(step.enabled === false ? 'disabled' : step.status)}`}>
                  {traceLabel(step)}
                </span>
              </div>
            ))}
          </div>
        </details>
      )}

      {factChecks.length > 0 && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-3">
          <p className="mb-2 text-sm font-medium text-yellow-400">팩트체크</p>
          <ul className="space-y-1 text-sm">
            {factChecks.map((fc, i) => (
              <li key={i} className="text-[var(--text-secondary)]">{fc}</li>
            ))}
          </ul>
        </div>
      )}

      {faq && (
        <div className="rounded-lg border border-[var(--border-primary)]">
          <button
            onClick={() => setFaqOpen(!faqOpen)}
            aria-label="FAQ 섹션 펼치기/접기"
            className="flex w-full items-center justify-between p-3 text-sm font-medium"
          >
            <span>자주 묻는 질문 (FAQ)</span>
            <span>{faqOpen ? '\u25B2' : '\u25BC'}</span>
          </button>
          {faqOpen && (
            <div className="border-t border-[var(--border-primary)] p-3 text-sm whitespace-pre-wrap">
              {faq}
            </div>
          )}
        </div>
      )}

      {sourcesUsed.length > 0 && (
        <div className="rounded-lg border border-[var(--border-primary)]">
          <button
            onClick={() => setSourcesOpen(!sourcesOpen)}
            aria-label="참고 소스 펼치기/접기"
            className="flex w-full items-center justify-between p-3 text-sm font-medium"
          >
            <span>참고 소스 ({sourcesUsed.length}개)</span>
            <span>{sourcesOpen ? '\u25B2' : '\u25BC'}</span>
          </button>
          {sourcesOpen && (
            <div className="border-t border-[var(--border-primary)] p-3">
              <ul className="space-y-1 text-sm">
                {sourcesUsed.map((s, i) => (
                  <li key={i}>
                    <span className="mr-1 text-xs text-[var(--text-tertiary)]">
                      {s.type === 'youtube' ? '\uD83C\uDFAC' : '\uD83D\uDCF0'}
                    </span>
                    <a href={s.url} target="_blank" rel="noopener noreferrer"
                       className="text-[var(--accent-primary)] hover:underline">
                      {s.title || s.url}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
