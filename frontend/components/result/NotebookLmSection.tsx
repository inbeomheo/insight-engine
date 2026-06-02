'use client';

import { Loader2, Download, ExternalLink, Music, Video, Image, FileText, Brain, HelpCircle, BookOpen, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';
import type { NotebookLmArtifact } from '@/lib/types';

const TYPE_META: Record<string, { label: string; icon: typeof Music }> = {
  audio: { label: '팟캐스트', icon: Music },
  video: { label: '비디오', icon: Video },
  infographic: { label: '인포그래픽', icon: Image },
  slide_deck: { label: '슬라이드', icon: FileText },
  mindmap: { label: '마인드맵', icon: Brain },
  quiz: { label: '퀴즈', icon: HelpCircle },
  flashcards: { label: '플래시카드', icon: BookOpen },
  briefing: { label: '브리핑', icon: FileText },
  study_guide: { label: '스터디 가이드', icon: BookOpen },
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
          <p className="text-xs text-indigo-900/60">?? ???, ???, ??? ???? ?? ??? ?????.</p>
        </div>
        <div className="flex flex-wrap gap-1.5 text-[11px]">
          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-emerald-700"><CheckCircle2 className="h-3 w-3" />?? {completed}</span>
          <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-indigo-700"><Loader2 className="h-3 w-3" />?? {running}</span>
          {failed > 0 && <span className="inline-flex items-center gap-1 rounded-full bg-white/80 px-2 py-1 text-red-700"><AlertTriangle className="h-3 w-3" />?? {failed}</span>}
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {artifacts.map((a) => {
          const meta = TYPE_META[a.content_type] ?? { label: a.content_type, icon: FileText };
          const Icon = meta.icon;

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
            <Button
              key={a.artifact_id}
              variant="outline"
              size="sm"
              className="h-8 rounded-xl bg-white/90 text-xs gap-1.5"
              onClick={() => window.open(apiUrl(`/api/notebooklm/view/${a.artifact_id}`), '_blank')}
            >
              <Icon className="h-3.5 w-3.5" />
              {meta.label} 보기
              <ExternalLink className="h-3 w-3" />
            </Button>
          );
        })}
      </div>
    </div>
  );
}
