'use client';

import { CalendarDays, CheckCircle2, Clock3, ExternalLink, FileText, Sparkles, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiUrl } from '@/lib/api';
import { getStyleLabel } from '@/lib/helpers';
import type { NotebookLmArtifact, Report } from '@/lib/types';
import { useSettingsStore } from '@/stores/settingsStore';
import { useUIStore } from '@/stores/uiStore';
import { getGenerationModeLabel, getModifierSummary, QUICK_ACTIONS } from './studioConfig';

interface StudioRightPanelProps {
  reports: Report[];
  sourceCount: number;
  schedulesCount: number;
}

const STATUS_META = {
  completed: { label: '완료', icon: CheckCircle2, className: 'bg-emerald-50 text-emerald-700' },
  in_progress: { label: '진행', icon: Clock3, className: 'bg-indigo-50 text-indigo-700' },
  failed: { label: '실패', icon: XCircle, className: 'bg-red-50 text-red-700' },
} as const;

const NLM_LABELS: Record<string, string> = {
  audio: '팟캐스트',
  video: '비디오',
  infographic: '인포그래픽',
  slide_deck: '슬라이드',
  mindmap: '마인드맵',
  quiz: '퀴즈',
  flashcards: '플래시카드',
  briefing: '브리핑',
  study_guide: '스터디 가이드',
};

const QUICK_ACTION_GUIDE: Record<string, { description: string; target: string }> = {
  export: { description: 'HTML, DOCX, MD, ZIP 저장으로 이동', target: '내보내기' },
  schedule: { description: '예약 캘린더와 발행 일정을 확인', target: '캘린더' },
  nlm: { description: 'NotebookLM 산출물 상태와 보기로 이동', target: 'NLM' },
  rewrite: { description: '플랫폼별 재작성 도구로 이동', target: '개선' },
  prompt: { description: '최근 결과의 생성 프롬프트 확인', target: '프롬프트' },
  settings: { description: '모델, 키, 워크스페이스 설정 열기', target: '설정' },
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
  const modelLabel = selectedModel || selectedProvider || '자동 선택';
  const modifierSummary = getModifierSummary(modifiers);

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
        <h2 className="mt-1 text-lg font-semibold text-slate-950">작업 요약</h2>
        <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{sourceCount}</p><p className="text-slate-500">소스</p></div>
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{reports.length}</p><p className="text-slate-500">결과</p></div>
          <div className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{nlmCount}</p><p className="text-slate-500">NLM</p></div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950">
          <Sparkles className="h-4 w-4 text-indigo-600" /> 현재 설정
        </div>
        <div className="mt-3 space-y-2 text-xs">
          <div data-testid="right-panel-setting-model" className="rounded-2xl bg-slate-50 p-3">
            <p className="text-slate-500">모델</p>
            <p className="mt-1 truncate font-semibold text-slate-900">{modelLabel}</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div data-testid="right-panel-setting-style" className="rounded-2xl bg-slate-50 p-3">
              <p className="text-slate-500">스타일</p>
              <p className="mt-1 font-semibold text-slate-900">{getStyleLabel(selectedStyle)}</p>
            </div>
            <div data-testid="right-panel-setting-mode" className="rounded-2xl bg-slate-50 p-3">
              <p className="text-slate-500">모드</p>
              <p className="mt-1 font-semibold text-slate-900">{getGenerationModeLabel(generationMode)}</p>
            </div>
          </div>
          <div data-testid="right-panel-modifier-summary" className="rounded-2xl bg-slate-50 p-3 text-slate-600">
            {modifierSummary}
          </div>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-indigo-600" /> 빠른 액션</div>
        <div data-testid="quick-action-workspace-status" className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
          <div className="rounded-2xl bg-emerald-50 px-2 py-2 text-emerald-700">
            <p className="text-sm font-bold">{reports.length}</p>
            <p>결과</p>
          </div>
          <div className="rounded-2xl bg-indigo-50 px-2 py-2 text-indigo-700">
            <p className="text-sm font-bold">{schedulesCount}</p>
            <p>예약</p>
          </div>
          <div className="rounded-2xl bg-violet-50 px-2 py-2 text-violet-700">
            <p className="text-sm font-bold">{nlmCount}</p>
            <p>NLM</p>
          </div>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            const guide = QUICK_ACTION_GUIDE[action.id] ?? { description: '작업 영역으로 이동', target: 'Workbench' };
            return (
              <button
                key={action.id}
                type="button"
                data-testid={`quick-action-${action.id}`}
                className="rounded-2xl bg-slate-50 p-3 text-left text-xs text-slate-600 transition hover:bg-indigo-50 hover:text-indigo-700"
                onClick={() => handleQuickAction(action.id)}
                aria-label={`${action.label} - ${guide.description}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <Icon className="h-4 w-4 text-indigo-600" />
                  <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-500">{guide.target}</span>
                </div>
                <p className="mt-2 font-semibold text-slate-800">{action.label}</p>
                <p data-testid={`quick-action-${action.id}-desc`} className="mt-1 line-clamp-2 text-[11px] leading-4 text-slate-500">
                  {guide.description}
                </p>
              </button>
            );
          })}
        </div>
      </section>

      <section data-testid="right-panel-nlm-artifacts" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-indigo-600" /> 최근 NLM 산출물</div>
        <div className="mt-3 space-y-2">
          {nlmArtifacts.length === 0 ? (
            <p className="text-xs text-slate-500">아직 NLM 산출물이 없습니다.</p>
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
                    보기 <ExternalLink className="h-3 w-3" />
                  </Button>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><FileText className="h-4 w-4 text-indigo-600" /> 최근 결과</div>
        <div className="mt-3 space-y-2">
          {latest.length === 0 ? <p className="text-xs text-slate-500">아직 생성된 결과가 없습니다.</p> : latest.map((report) => <div key={report.id} className="rounded-2xl bg-slate-50 p-3"><p className="line-clamp-2 text-xs font-medium text-slate-800">{report.title}</p><p className="mt-1 text-[11px] text-slate-500">{report.style}</p></div>)}
        </div>
      </section>
      <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><CalendarDays className="h-4 w-4 text-indigo-600" /> 예약</div>
        <p className="mt-2 text-xs text-slate-500">예약된 발행 {schedulesCount}개</p>
      </section>
    </div>
  );
}
