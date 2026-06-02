'use client';

import { CalendarDays, CheckCircle2, Clock3, ExternalLink, FileText, Sparkles, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';
import { getStyleLabel } from '@/lib/helpers';
import type { NotebookLmArtifact, Report } from '@/lib/types';
import { useSettingsStore } from '@/stores/settingsStore';
import { useUIStore } from '@/stores/uiStore';
import { QUICK_ACTIONS } from './studioConfig';

interface StudioRightPanelProps {
  reports: Report[];
  sourceCount: number;
  schedulesCount: number;
}

const MODE_LABELS: Record<string, string> = {
  individual: '?? ??',
  combined: '?? ???',
  fusion: '?? ??',
};

const STATUS_META = {
  completed: { label: '??', icon: CheckCircle2, className: 'bg-emerald-50 text-emerald-700' },
  in_progress: { label: '??', icon: Clock3, className: 'bg-indigo-50 text-indigo-700' },
  failed: { label: '??', icon: XCircle, className: 'bg-red-50 text-red-700' },
} as const;

const NLM_LABELS: Record<string, string> = {
  audio: '????',
  video: '???',
  infographic: '?????',
  slide_deck: '????',
  mindmap: '????',
  quiz: '??',
  flashcards: '?????',
  briefing: '???',
  study_guide: '??? ???',
};

function flattenArtifacts(reports: Report[]) {
  return reports.flatMap((report) =>
    (report.notebooklm?.artifacts ?? []).map((artifact) => ({ artifact, report })),
  );
}

function artifactStatus(artifact: NotebookLmArtifact) {
  return STATUS_META[artifact.status as keyof typeof STATUS_META] ?? STATUS_META.in_progress;
}

export default function StudioRightPanel({ reports, sourceCount, schedulesCount }: StudioRightPanelProps) {
  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const selectedProvider = useSettingsStore((s) => s.selectedProvider);
  const selectedStyle = useSettingsStore((s) => s.selectedStyle);
  const generationMode = useSettingsStore((s) => s.generationMode);
  const modifiers = useSettingsStore((s) => s.modifiers);
  const setActiveView = useUIStore((s) => s.setActiveView);
  const setActiveReportId = useUIStore((s) => s.setActiveReportId);
  const setSettingsModalOpen = useUIStore((s) => s.setSettingsModalOpen);
  const setPromptModalOpen = useUIStore((s) => s.setPromptModalOpen);

  const nlmArtifacts = flattenArtifacts(reports).slice(0, 6);
  const nlmCount = reports.reduce((sum, report) => sum + (report.notebooklm?.artifacts?.length ?? 0), 0);
  const latest = reports.slice(0, 4);
  const firstReport = reports[0];
  const modelLabel = selectedModel || selectedProvider || '?? ??';

  function scrollTo(selector: string) {
    document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function handleQuickAction(id: string) {
    if (id === 'schedule') {
      setActiveView('calendar');
      return;
    }
    if (id === 'settings') {
      setSettingsModalOpen(true);
      return;
    }
    if (id === 'prompt') {
      if (firstReport?.prompt) {
        setPromptModalOpen(true, firstReport.prompt);
        setActiveReportId(firstReport.id);
      }
      return;
    }
    if (id === 'nlm') {
      scrollTo('[data-testid="notebooklm-artifact"], [data-testid="result-workbench"]');
      return;
    }
    scrollTo('[data-testid="result-workbench"]');
  }

  return (
    <div data-testid="studio-right-panel" className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Workspace</p>
        <h2 className="mt-1 text-lg font-semibold text-slate-950">?? ??</h2>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{sourceCount}</p><p className="text-slate-500">??</p></div>
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{reports.length}</p><p className="text-slate-500">??</p></div>
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{nlmCount}</p><p className="text-slate-500">NLM</p></div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
          <Sparkles className="h-4 w-4 text-indigo-600" /> ?? ??
        </div>
        <div className="mt-3 space-y-2 text-xs">
          <div data-testid="right-panel-setting-model" className="rounded-2xl bg-slate-50 p-3">
            <p className="text-slate-500">??</p>
            <p className="mt-1 truncate font-semibold text-slate-900">{modelLabel}</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div data-testid="right-panel-setting-style" className="rounded-2xl bg-slate-50 p-3">
              <p className="text-slate-500">???</p>
              <p className="mt-1 font-semibold text-slate-900">{getStyleLabel(selectedStyle)}</p>
            </div>
            <div data-testid="right-panel-setting-mode" className="rounded-2xl bg-slate-50 p-3">
              <p className="text-slate-500">??</p>
              <p className="mt-1 font-semibold text-slate-900">{MODE_LABELS[generationMode] ?? generationMode}</p>
            </div>
          </div>
          <div className="rounded-2xl bg-slate-50 p-3 text-slate-600">
            {modifiers.length} ? {modifiers.writing_style} ? {modifiers.language}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-indigo-600" /> ?? ??</div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.id}
                type="button"
                data-testid={`quick-action-${action.id}`}
                className="rounded-2xl bg-slate-50 p-3 text-left text-xs text-slate-600 transition hover:bg-indigo-50 hover:text-indigo-700"
                onClick={() => handleQuickAction(action.id)}
              >
                <Icon className="mb-2 h-4 w-4 text-indigo-600" />{action.label}
              </button>
            );
          })}
        </div>
      </section>

      <section data-testid="right-panel-nlm-artifacts" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-indigo-600" /> ?? NLM ???</div>
        <div className="mt-3 space-y-2">
          {nlmArtifacts.length === 0 ? (
            <p className="text-xs text-slate-500">?? NLM ???? ????.</p>
          ) : nlmArtifacts.map(({ artifact, report }) => {
            const status = artifactStatus(artifact);
            const StatusIcon = status.icon;
            return (
              <div key={artifact.artifact_id} data-testid="right-panel-nlm-artifact" className="rounded-2xl bg-slate-50 p-3 text-xs">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{NLM_LABELS[artifact.content_type] ?? artifact.content_type}</p>
                    <p className="mt-1 truncate text-[11px] text-slate-500">{report.title}</p>
                  </div>
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] ${status.className}`}>
                    <StatusIcon className="h-3 w-3" />{status.label}
                  </span>
                </div>
                {artifact.status === 'completed' && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mt-2 h-7 gap-1 rounded-lg px-2 text-xs"
                    onClick={() => window.open(apiUrl(`/api/notebooklm/view/${artifact.artifact_id}`), '_blank')}
                  >
                    ?? <ExternalLink className="h-3 w-3" />
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><FileText className="h-4 w-4 text-indigo-600" /> ?? ??</div>
        <div className="mt-3 space-y-2">
          {latest.length === 0 ? <p className="text-xs text-slate-500">?? ??? ??? ????.</p> : latest.map((report) => <div key={report.id} className="rounded-2xl bg-slate-50 p-3"><p className="line-clamp-2 text-xs font-medium text-slate-800">{report.title}</p><p className="mt-1 text-[11px] text-slate-500">{report.style}</p></div>)}
        </div>
      </section>
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><CalendarDays className="h-4 w-4 text-indigo-600" /> ??</div>
        <p className="mt-2 text-xs text-slate-500">??? ?? {schedulesCount}?</p>
      </section>
    </div>
  );
}
