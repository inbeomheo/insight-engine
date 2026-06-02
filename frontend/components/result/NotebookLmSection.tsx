'use client';

import { Loader2, Download, ExternalLink, Music, Video, Image, FileText, Brain, HelpCircle, BookOpen, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';
import type { NotebookLmArtifact } from '@/lib/types';

const TYPE_META: Record<string, { label: string; icon: typeof Music; downloadLabel?: string }> = {
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

interface NotebookLmSectionProps {
  artifacts: NotebookLmArtifact[];
}

export function NotebookLmSection({ artifacts }: NotebookLmSectionProps) {
  if (!artifacts || artifacts.length === 0) return null;

  const completed = artifacts.filter((a) => a.status === 'completed').length;
  const running = artifacts.filter((a) => a.status === 'in_progress').length;
  const failed = artifacts.filter((a) => a.status === 'failed').length;

  return (
    <div className="mt-4 rounded-2xl border border-indigo-100 bg-indigo-50/50 p-3">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-indigo-700">NotebookLM Artifacts</p>
          <p className="text-xs text-indigo-900/60">브라우저 보기는 화면에서 읽기용으로 열고, HTML 저장은 Markdown 산출물을 웹 문서로 저장합니다. PDF/MP3/MP4는 원본 형식 그대로 받습니다.</p>
        </div>
        <div className="flex flex-wrap gap-1.5 text-[11px]">
          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-emerald-700"><CheckCircle2 className="h-3 w-3" />완료 {completed}</span>
          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-indigo-700"><Loader2 className="h-3 w-3" />진행 {running}</span>
          {failed > 0 && <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-red-700"><AlertTriangle className="h-3 w-3" />실패 {failed}</span>}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {artifacts.map((a) => {
          const meta = TYPE_META[a.content_type] ?? { label: a.content_type, icon: FileText };
          const Icon = meta.icon;
          const isMarkdownArtifact = (meta.downloadLabel ?? 'MD') === 'MD';
          const downloadUrl = isMarkdownArtifact
            ? `/api/notebooklm/rendered-download/${a.artifact_id}`
            : `/api/notebooklm/download/${a.artifact_id}`;
          const downloadLabel = isMarkdownArtifact
            ? 'HTML 저장'
            : `원본 ${meta.downloadLabel ?? '파일'} 저장`;

          if (a.status === 'in_progress') {
            return (
              <div key={a.artifact_id} className="flex items-center gap-1.5 rounded-xl border border-indigo-100 bg-white/80 px-3 py-2 text-xs text-indigo-800 shadow-sm">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>{meta.label} 생성 중...</span>
              </div>
            );
          }

          if (a.status === 'failed') {
            return (
              <div key={a.artifact_id} className="flex items-center gap-1.5 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">
                <Icon className="h-3.5 w-3.5" />
                <span>{meta.label} 실패</span>
              </div>
            );
          }

          // completed
          if (a.content_type === 'audio') {
            return (
              <div key={a.artifact_id} className="w-full">
                <div className="flex items-center gap-2 mb-1">
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium">{meta.label}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 ml-auto"
                    onClick={() => window.open(apiUrl(`/api/notebooklm/download/${a.artifact_id}`), '_blank')}
                  >
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <audio controls className="w-full h-8" preload="none">
                  <source src={apiUrl(`/api/notebooklm/download/${a.artifact_id}`)} />
                </audio>
              </div>
            );
          }

          return (
            <div
              key={a.artifact_id}
              data-testid="notebooklm-artifact"
              className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-100 bg-white/90 px-2 py-1.5 text-xs shadow-sm"
            >
              <Icon className="h-3.5 w-3.5 text-indigo-700" />
              <span className="font-medium text-slate-700">{meta.label}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                data-testid="notebooklm-view-artifact"
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
                className="h-6 gap-1 rounded-lg px-2 text-xs text-muted-foreground"
                onClick={() => window.open(apiUrl(downloadUrl), '_blank')}
              >
                {downloadLabel}
                <Download className="h-3 w-3" />
              </Button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
