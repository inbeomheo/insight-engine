'use client';

import {
  AlertTriangle,
  BookOpen,
  Brain,
  CheckCircle2,
  Download,
  ExternalLink,
  FileText,
  HelpCircle,
  Image,
  Loader2,
  Music,
  Video,
  type LucideIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';
import type { NotebookLmArtifact } from '@/lib/types';

const TYPE_META: Record<string, { label: string; icon: LucideIcon; downloadLabel?: string }> = {
  audio: { label: '팟캐스트', icon: Music, downloadLabel: 'MP3' },
  video: { label: '비디오', icon: Video, downloadLabel: 'MP4' },
  infographic: { label: '인포그래픽', icon: Image, downloadLabel: 'MD' },
  slide_deck: { label: '슬라이드', icon: FileText, downloadLabel: 'PDF' },
  mindmap: { label: '마인드맵', icon: Brain, downloadLabel: 'MD' },
  quiz: { label: '퀴즈', icon: HelpCircle, downloadLabel: 'MD' },
  flashcards: { label: '플래시카드', icon: BookOpen, downloadLabel: 'MD' },
  briefing: { label: '브리핑', icon: FileText, downloadLabel: 'MD' },
  study_guide: { label: '스터디 가이드', icon: BookOpen, downloadLabel: 'MD' },
};

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function markdownFallbackHtml(markdown: string, title: string) {
  const safeTitle = escapeHtml(title);
  return `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${safeTitle}</title>
  <style>
    body { max-width: 860px; margin: 40px auto; padding: 0 20px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.7; color: #111827; }
    pre { white-space: pre-wrap; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; }
  </style>
</head>
<body><pre>${escapeHtml(markdown)}</pre></body>
</html>`;
}

function downloadHtml(html: string, filename: string) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function saveMarkdownArtifactAsHtml(artifactId: string) {
  const response = await fetch(apiUrl(`/api/notebooklm/rendered-download/${artifactId}`));
  if (!response.ok) throw new Error(`NotebookLM HTML 저장 실패: HTTP ${response.status}`);

  const text = await response.text();
  const trimmed = text.trimStart().toLowerCase();
  const isHtml = response.headers.get('content-type')?.includes('text/html')
    || trimmed.startsWith('<!doctype')
    || trimmed.startsWith('<html');
  const filename = `${artifactId}.html`;
  downloadHtml(isHtml ? text : markdownFallbackHtml(text, filename), filename);
}

interface NotebookLmSectionProps {
  artifacts: NotebookLmArtifact[];
}

export function NotebookLmSection({ artifacts }: NotebookLmSectionProps) {
  if (!artifacts || artifacts.length === 0) return null;

  const completed = artifacts.filter((a) => a.status === 'completed').length;
  const running = artifacts.filter((a) => a.status === 'in_progress').length;
  const failed = artifacts.filter((a) => a.status === 'failed').length;
  const statusText = `완료 ${completed}개, 진행 ${running}개, 실패 ${failed}개`;

  return (
    <section
      data-testid="notebooklm-artifacts-panel"
      role="region"
      aria-label="NotebookLM 산출물"
      className="mt-4 rounded-2xl border border-indigo-100 bg-indigo-50/50 p-3"
    >
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-700">NotebookLM Artifacts</p>
          <p className="text-xs text-indigo-900/60">브라우저 보기는 별도 화면에서 읽기 전용으로 열고, HTML 저장은 Markdown 산출물을 웹 문서로 저장합니다. PDF/MP3/MP4는 원본 형식 그대로 받습니다.</p>
        </div>
        <div
          data-testid="notebooklm-artifact-status"
          role="status"
          aria-live="polite"
          aria-label={statusText}
          className="flex flex-wrap gap-1.5 text-[11px]"
        >
          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-emerald-700"><CheckCircle2 className="h-3 w-3" />완료 {completed}</span>
          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-indigo-700"><Loader2 className="h-3 w-3" />진행 {running}</span>
          {failed > 0 && <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-red-700"><AlertTriangle className="h-3 w-3" />실패 {failed}</span>}
        </div>
      </div>
      <div data-testid="notebooklm-artifact-list" role="list" className="flex flex-wrap gap-2">
        {artifacts.map((a) => {
          const meta = TYPE_META[a.content_type] ?? { label: a.content_type, icon: FileText };
          const Icon = meta.icon;
          const isMarkdownArtifact = (meta.downloadLabel ?? 'MD') === 'MD';
          const downloadLabel = isMarkdownArtifact ? 'HTML 저장' : `원본 ${meta.downloadLabel ?? '파일'} 저장`;

          if (a.status === 'in_progress') {
            return (
              <div
                key={a.artifact_id}
                data-testid="notebooklm-artifact"
                role="listitem"
                aria-label={`${meta.label} 생성 진행 중`}
                className="flex items-center gap-1.5 rounded-xl border border-indigo-100 bg-white/80 px-3 py-2 text-xs text-indigo-800 shadow-sm"
              >
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>{meta.label} 생성 중...</span>
              </div>
            );
          }

          if (a.status === 'failed') {
            return (
              <div
                key={a.artifact_id}
                data-testid="notebooklm-artifact"
                role="listitem"
                aria-label={`${meta.label} 생성 실패`}
                className="flex items-center gap-1.5 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700"
              >
                <Icon className="h-3.5 w-3.5" />
                <span>{meta.label} 실패</span>
              </div>
            );
          }

          if (a.content_type === 'audio') {
            return (
              <div
                key={a.artifact_id}
                data-testid="notebooklm-artifact"
                role="listitem"
                aria-label={`${meta.label} 완료`}
                className="w-full rounded-xl border border-indigo-100 bg-white/90 p-2 shadow-sm"
              >
                <div className="mb-1 flex items-center gap-2">
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium">{meta.label}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="ml-auto h-6 w-6"
                    aria-label={`${meta.label} ${downloadLabel}`}
                    onClick={() => window.open(apiUrl(`/api/notebooklm/download/${a.artifact_id}`), '_blank')}
                  >
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <audio controls className="h-8 w-full" preload="none">
                  <source src={apiUrl(`/api/notebooklm/download/${a.artifact_id}`)} />
                </audio>
              </div>
            );
          }

          return (
            <div
              key={a.artifact_id}
              data-testid="notebooklm-artifact"
              role="listitem"
              aria-label={`${meta.label} 완료`}
              className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-100 bg-white/90 px-2 py-1.5 text-xs shadow-sm"
            >
              <Icon className="h-3.5 w-3.5 text-indigo-700" />
              <span className="font-medium text-slate-700">{meta.label}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                data-testid="notebooklm-view-artifact"
                aria-label={`${meta.label} 브라우저 보기`}
                className="h-6 gap-1 rounded-lg px-2 text-xs"
                onClick={() => window.open(apiUrl(`/api/notebooklm/view/${a.artifact_id}`), '_blank')}
              >
                브라우저 보기
                <ExternalLink className="h-3 w-3" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                data-testid="notebooklm-download-artifact"
                aria-label={`${meta.label} ${downloadLabel}`}
                className="h-6 gap-1 rounded-lg px-2 text-xs text-muted-foreground"
                onClick={() => {
                  if (isMarkdownArtifact) {
                    void saveMarkdownArtifactAsHtml(a.artifact_id);
                  } else {
                    window.open(apiUrl(`/api/notebooklm/download/${a.artifact_id}`), '_blank');
                  }
                }}
              >
                {downloadLabel}
                <Download className="h-3 w-3" />
              </Button>
            </div>
          );
        })}
      </div>
    </section>
  );
}
