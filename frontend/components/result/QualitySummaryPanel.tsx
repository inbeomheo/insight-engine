'use client';

import type {
  FusionQualityStatus,
  FusionQualitySummary,
  GenerationQualitySummary,
  QualitySummary,
} from '@/lib/types';

interface QualitySummaryPanelProps {
  summary?: QualitySummary;
  title?: string;
  model?: string;
  warnings?: string[];
  className?: string;
}

const QUALITY_LABELS: Record<FusionQualityStatus, string> = {
  ok: '정상',
  warning: '주의',
  error: '오류',
  disabled: '없음',
};

const SOURCE_LABELS: Record<string, string> = {
  youtube: 'YouTube 자막',
  merged_youtube: '통합 YouTube 자막',
  direct_input: '직접 입력',
  voice: '음성 전사',
  document: '문서 본문',
  webpage: '웹페이지 본문',
  rss: 'RSS 본문',
  arxiv: 'arXiv 초록',
  twitter: 'Twitter 게시물',
  reddit: 'Reddit 포스트',
  github: 'GitHub README',
  hackernews: 'Hacker News 게시물',
  podcast: '팟캐스트 전사',
  regenerate: '재생성 원문',
};

function isGenerationSummary(summary: QualitySummary): summary is GenerationQualitySummary {
  return typeof summary === 'object' && summary !== null && 'kind' in summary && summary.kind === 'generation';
}

function statusClass(status?: FusionQualityStatus): string {
  if (status === 'warning') return 'border-yellow-500/30 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400';
  if (status === 'error') return 'border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400';
  if (status === 'disabled') return 'border-border bg-muted/40 text-muted-foreground';
  return 'border-green-500/30 bg-green-500/10 text-green-600 dark:text-green-400';
}

function qualityLabel(status?: FusionQualityStatus): string {
  return status ? QUALITY_LABELS[status] : '확인 전';
}

function sourceLabel(type?: string): string {
  if (!type) return '알 수 없는 원본';
  return SOURCE_LABELS[type] ?? type;
}

function countText(count: number): string {
  return `${count.toLocaleString()}자`;
}

function QualityItem({
  label,
  status,
  detail,
}: {
  label: string;
  status?: FusionQualityStatus;
  detail: string;
}) {
  return (
    <div className="min-w-0 rounded-md border border-border/60 bg-background/60 px-3 py-2">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="truncate text-xs font-medium text-foreground">{label}</span>
        <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] ${statusClass(status)}`}>
          {qualityLabel(status)}
        </span>
      </div>
      <p className="break-words text-xs leading-5 text-muted-foreground">{detail}</p>
    </div>
  );
}

function FusionQualityItems({ summary }: { summary: FusionQualitySummary }) {
  return (
    <div className="grid gap-2 sm:grid-cols-3">
      <QualityItem
        label="소스 커버리지"
        status={summary.source_coverage?.status}
        detail={`${summary.source_coverage?.collected_count ?? 0}/${summary.source_coverage?.requested_count ?? 0}개 수집 · 요약 ${summary.source_coverage?.summary_count ?? 0}개`}
      />
      <QualityItem
        label="댓글 반영"
        status={summary.comment_reflection?.status}
        detail={
          summary.comment_reflection?.enabled
            ? `${summary.comment_reflection.collected_count ?? 0}개 수집 · ${summary.comment_reflection.analyzed_count ?? 0}개 반영`
            : '댓글 분석 없음'
        }
      />
      <QualityItem
        label="웹 리서치"
        status={summary.web_research?.status}
        detail={
          summary.web_research?.enabled
            ? `외부 소스 ${summary.web_research.sources_found ?? 0}개`
            : '웹 리서치 없음'
        }
      />
    </div>
  );
}

function GenerationQualityItems({ summary }: { summary: GenerationQualitySummary }) {
  const source = summary.source ?? {
    status: 'error' as const,
    type: 'unknown',
    has_content: false,
    char_count: 0,
  };
  const comments = summary.comments ?? {
    status: 'disabled' as const,
    available_count: 0,
    reflected: false,
  };
  const body = summary.body ?? {
    status: 'error' as const,
    has_title: false,
    has_content: false,
    has_html: false,
    char_count: 0,
  };

  const sourceDetail = [
    sourceLabel(source.type),
    countText(source.char_count ?? 0),
    source.transcript_source ? `출처 ${source.transcript_source}` : null,
  ].filter(Boolean).join(' · ');

  const commentDetail = comments.available_count > 0
    ? `${comments.available_count.toLocaleString()}개 수집 · ${comments.reflected ? '반영됨' : '미반영'}`
    : comments.reflected ? '댓글 요약 반영됨' : '댓글 없음 또는 수집 안 됨';

  const bodyFlags = [
    body.has_title ? '제목 있음' : '제목 없음',
    body.has_content ? countText(body.char_count ?? 0) : '본문 없음',
    body.has_html ? 'HTML 있음' : 'HTML 없음',
  ].join(' · ');

  return (
    <div className="grid gap-2 sm:grid-cols-3">
      <QualityItem label="원본" status={source.status} detail={sourceDetail} />
      <QualityItem label="댓글" status={comments.status} detail={commentDetail} />
      <QualityItem label="본문" status={body.status} detail={bodyFlags} />
    </div>
  );
}

export default function QualitySummaryPanel({
  summary,
  title,
  model,
  warnings,
  className,
}: QualitySummaryPanelProps) {
  if (!summary) return null;

  const isGeneration = isGenerationSummary(summary);
  const warningItems = warnings ?? summary.warnings ?? [];
  const heading = title ?? (isGeneration ? '품질/진단 점검' : '퓨전 품질 점검');

  return (
    <section className={`rounded-md border border-border/70 bg-muted/20 p-3 ${className ?? ''}`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{heading}</p>
          {model && (
            <p className="mt-0.5 break-all text-xs text-muted-foreground">모델 {model}</p>
          )}
        </div>
        <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs ${statusClass(summary.status)}`}>
          {qualityLabel(summary.status)}
        </span>
      </div>

      {isGeneration ? (
        <GenerationQualityItems summary={summary} />
      ) : (
        <FusionQualityItems summary={summary} />
      )}

      {warningItems.length > 0 && (
        <ul className="mt-3 space-y-1 text-xs leading-5 text-yellow-600 dark:text-yellow-400">
          {warningItems.slice(0, 3).map((warning, i) => (
            <li key={`${warning}-${i}`} className="break-words">- {warning}</li>
          ))}
          {warningItems.length > 3 && <li>외 {warningItems.length - 3}개 경고</li>}
        </ul>
      )}
    </section>
  );
}
