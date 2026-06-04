'use client';

import { useState } from 'react';
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
  generationMode: string;
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

const DETAIL_LABELS = {
  brief: '간단',
  standard: '표준',
  deep: '심층',
} as const;

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

function buildWorkspaceMarkdown(reports: Report[]) {
  const createdAt = new Date().toLocaleString('ko-KR');
  const body = reports.map((report, index) => [
    `## ${index + 1}. ${report.title || '제목 없음'}`,
    '',
    `- 스타일: ${getStyleLabel(report.style)}`,
    `- 소스: ${report.url || report.youtube_title || '텍스트/파일 소스'}`,
    `- 생성 시간: ${report.time || '-'}`,
    '',
    report.content || report.html || '',
  ].join('\n')).join('\n\n---\n\n');

  return [
    '# Insight Studio 전체 내보내기',
    '',
    `- 내보낸 시간: ${createdAt}`,
    `- 결과 수: ${reports.length}개`,
    '',
    '---',
    '',
    body,
  ].join('\n');
}

function downloadMarkdown(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function StudioRightPanel({ reports, sourceCount, schedulesCount, generationMode }: StudioRightPanelProps) {
  const [quickNotice, setQuickNotice] = useState<string | null>(null);
  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const selectedProvider = useSettingsStore((s) => s.selectedProvider);
  const selectedStyle = useSettingsStore((s) => s.selectedStyle);
  const modifiers = useSettingsStore((s) => s.modifiers);
  const detailLevel = useSettingsStore((s) => s.detailLevel);
  const enableWebSearch = useSettingsStore((s) => s.enableWebSearch);
  const enableWebResearch = useSettingsStore((s) => s.enableWebResearch);
  const enableDeepComments = useSettingsStore((s) => s.enableDeepComments);
  const enableAgentMode = useSettingsStore((s) => s.enableAgentMode);
  const setActiveView = useUIStore((s) => s.setActiveView);
  const setActiveReportId = useUIStore((s) => s.setActiveReportId);
  const setSettingsModalOpen = useUIStore((s) => s.setSettingsModalOpen);
  const setPromptModalOpen = useUIStore((s) => s.setPromptModalOpen);

  const nlmArtifacts = flattenArtifacts(reports).slice(0, 6);
  const nlmCount = reports.reduce((sum, report) => sum + (report.notebooklm?.artifacts?.length ?? 0), 0);
  const latest = reports.slice(0, 4);
  const firstReport = reports[0];
  const firstCompletedNlm = nlmArtifacts.find(({ artifact }) => artifact.status === 'completed');
  const modelLabel = selectedModel || selectedProvider || '자동 선택';
  const selectedStyleLabel = getStyleLabel(selectedStyle);
  const selectedModeLabel = getGenerationModeLabel(generationMode);
  const modifierSummary = getModifierSummary(modifiers);
  const advancedSummary = [
    `상세도 ${DETAIL_LABELS[detailLevel]}`,
    `웹 보강 ${enableWebSearch ? '켜짐' : '꺼짐'}`,
    `웹 리서치 ${enableWebResearch ? '켜짐' : '꺼짐'}`,
    `댓글 ${enableDeepComments ? '켜짐' : '꺼짐'}`,
    `에이전트 ${enableAgentMode ? '켜짐' : '꺼짐'}`,
  ].join(' · ');

  const workspaceStatusLabel = `\uacb0\uacfc ${reports.length}\uac1c, \uc608\uc57d ${schedulesCount}\uac1c, NLM ${nlmCount}\uac1c`;
  const scheduleLabel = `\uc608\uc57d \uce98\ub9b0\ub354 \uc5f4\uae30, \uc608\uc57d\ub41c \ubc1c\ud589 ${schedulesCount}\uac1c`;

  function scrollTo(selector: string) {
    document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function handleExportAll() {
    if (reports.length === 0) {
      setQuickNotice('내보낼 결과가 없습니다');
      scrollTo('[data-testid="result-workbench"]');
      return;
    }

    const date = new Date().toISOString().slice(0, 10);
    downloadMarkdown(`insight-studio-export-${date}.md`, buildWorkspaceMarkdown(reports));
    setQuickNotice(`전체 내보내기 완료 · ${reports.length}개 결과`);
  }

  function focusReport(reportId: string) {
    setActiveReportId(reportId);
    window.dispatchEvent(new CustomEvent('insight-engine-focus-report', { detail: { reportId } }));
    document.querySelector(`[data-report-id="${reportId}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function handleQuickAction(id: string) {
    const requireResult = (message: string) => {
      setQuickNotice(`먼저 결과를 생성하세요 · ${message}`);
      scrollTo('[data-testid="result-workbench"]');
    };

    if (id === 'export') {
      handleExportAll();
      return;
    }
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
      } else {
        requireResult('프롬프트 확인은 생성 결과가 필요합니다');
      }
      return;
    }
    if (id === 'nlm') {
      if (firstCompletedNlm) {
        window.open(apiUrl(`/api/notebooklm/view/${firstCompletedNlm.artifact.artifact_id}`), '_blank');
        return;
      }
      if (reports.length === 0) {
        requireResult('NLM 산출물은 결과 생성 후 확인할 수 있습니다');
        return;
      }
      scrollTo('[data-testid="notebooklm-artifact"], [data-testid="result-workbench"]');
      return;
    }
    if (id === 'rewrite') {
      if (firstReport) {
        setActiveReportId(firstReport.id);
        window.dispatchEvent(new CustomEvent('insight-engine-open-rewrite', { detail: { reportId: firstReport.id } }));
      } else {
        requireResult('플랫폼 변환은 생성 결과가 필요합니다');
      }
      scrollTo('[data-testid="result-workbench"]');
      return;
    }
    scrollTo('[data-testid="result-workbench"]');
  }

  return (
    <div data-testid="studio-right-panel" className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <section data-testid="right-panel-workspace-section" role="region" aria-labelledby="right-panel-workspace-title" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Workspace</p>
        <h2 id="right-panel-workspace-title" className="mt-1 text-lg font-semibold text-slate-950">작업 요약</h2>
        <div data-testid="right-panel-workspace-metrics" role="list" aria-label="작업 요약 지표" className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
          <div data-testid="right-panel-workspace-source-count" role="listitem" aria-label={`소스 ${sourceCount}개`} className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{sourceCount}</p><p className="text-slate-500">소스</p></div>
          <div data-testid="right-panel-workspace-result-count" role="listitem" aria-label={`결과 ${reports.length}개`} className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{reports.length}</p><p className="text-slate-500">결과</p></div>
          <div data-testid="right-panel-workspace-nlm-count" role="listitem" aria-label={`NLM ${nlmCount}개`} className="rounded-2xl bg-slate-50 p-3"><p className="text-lg font-bold text-slate-950">{nlmCount}</p><p className="text-slate-500">NLM</p></div>
        </div>
      </section>

      <section data-testid="right-panel-settings-section" role="region" aria-labelledby="right-panel-settings-title" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div id="right-panel-settings-title" className="flex items-center gap-2 text-sm font-semibold text-slate-950">
          <Sparkles className="h-4 w-4 text-indigo-600" /> 현재 설정
        </div>
        <div data-testid="right-panel-settings-list" role="list" aria-label="현재 설정 요약" className="mt-3 space-y-2 text-xs">
          <div data-testid="right-panel-setting-model" role="listitem" aria-label={`모델 ${modelLabel}`} className="rounded-2xl bg-slate-50 p-3">
            <p className="text-slate-500">모델</p>
            <p className="mt-1 truncate font-semibold text-slate-900">{modelLabel}</p>
          </div>
          <div role="presentation" className="grid grid-cols-2 gap-2">
            <div data-testid="right-panel-setting-style" role="listitem" aria-label={`스타일 ${selectedStyleLabel}`} className="rounded-2xl bg-slate-50 p-3">
              <p className="text-slate-500">스타일</p>
              <p className="mt-1 font-semibold text-slate-900">{selectedStyleLabel}</p>
            </div>
            <div data-testid="right-panel-setting-mode" role="listitem" aria-label={`모드 ${selectedModeLabel}`} className="rounded-2xl bg-slate-50 p-3">
              <p className="text-slate-500">모드</p>
              <p className="mt-1 font-semibold text-slate-900">{selectedModeLabel}</p>
            </div>
          </div>
          <div data-testid="right-panel-modifier-summary" role="listitem" aria-label={`세부 옵션 ${modifierSummary}`} className="rounded-2xl bg-slate-50 p-3 text-slate-600">
            {modifierSummary}
          </div>
          <div data-testid="right-panel-advanced-summary" role="listitem" aria-label={`고급 옵션 ${advancedSummary}`} className="rounded-2xl bg-slate-50 p-3 text-slate-600">
            {advancedSummary}
          </div>
        </div>
      </section>

      <section data-testid="right-panel-actions-section" role="region" aria-labelledby="right-panel-actions-title" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div id="right-panel-actions-title" className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-indigo-600" /> 빠른 액션</div>
        <div data-testid="quick-action-workspace-status" role="status" aria-live="polite" aria-label={workspaceStatusLabel} className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
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
        {quickNotice && (
          <div
            data-testid="quick-action-export-status" role="status" aria-live="polite"
            className="mt-3 rounded-2xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700"
          >
            {quickNotice}
          </div>
        )}
        <div className="mt-3 grid grid-cols-2 gap-2">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon;
            const guide = QUICK_ACTION_GUIDE[action.id] ?? { description: '작업 영역으로 이동', target: 'Workbench' };
            const actionHref = action.id === 'nlm' && firstCompletedNlm
              ? apiUrl(`/api/notebooklm/view/${firstCompletedNlm.artifact.artifact_id}`)
              : null;
            const actionClassName = 'block rounded-2xl bg-slate-50 p-3 text-left text-xs text-slate-600 transition hover:bg-indigo-50 hover:text-indigo-700';
            const actionContent = (
              <>
                <div className="pointer-events-none flex items-center justify-between gap-2">
                  <Icon className="h-4 w-4 text-indigo-600" />
                  <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-slate-500">{guide.target}</span>
                </div>
                <p className="pointer-events-none mt-2 font-semibold text-slate-800">{action.label}</p>
                <p data-testid={`quick-action-${action.id}-desc`} className="pointer-events-none mt-1 line-clamp-2 text-[11px] leading-4 text-slate-500">
                  {guide.description}
                </p>
              </>
            );
            if (actionHref) {
              return (
                <a
                  key={action.id}
                  data-testid={`quick-action-${action.id}`}
                  className={actionClassName}
                  href={actionHref}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(event) => {
                    event.preventDefault();
                    window.open(actionHref, '_blank', 'noreferrer');
                  }}
                  aria-label={`${action.label} - ${guide.description}`}
                >
                  {actionContent}
                </a>
              );
            }
            return (
              <button
                key={action.id}
                type="button"
                data-testid={`quick-action-${action.id}`}
                className={actionClassName}
                onClick={() => handleQuickAction(action.id)}
                aria-label={`${action.label} - ${guide.description}`}
              >
                {actionContent}
              </button>
            );
          })}
        </div>
      </section>

      <section data-testid="right-panel-nlm-artifacts" role="region" aria-labelledby="right-panel-nlm-title" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div id="right-panel-nlm-title" className="flex items-center gap-2 text-sm font-semibold text-slate-950"><Sparkles className="h-4 w-4 text-indigo-600" /> 최근 NLM 산출물</div>
        <div data-testid="right-panel-nlm-list" role="list" aria-label="최근 NotebookLM 산출물" className="mt-3 space-y-2">
          {nlmArtifacts.length === 0 ? (
            <p className="text-xs text-slate-500">아직 NLM 산출물이 없습니다.</p>
          ) : nlmArtifacts.map(({ artifact, report }) => {
            const status = artifactStatus(artifact);
            const StatusIcon = status.icon;
            const artifactLabel = NLM_LABELS[artifact.content_type] ?? artifact.content_type;
            return (
              <div key={artifact.artifact_id} data-testid="right-panel-nlm-artifact" role="listitem" aria-label={`${artifactLabel} · ${report.title} · 상태 ${status.label}`} className="rounded-2xl bg-slate-50 p-3 text-xs">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900">{artifactLabel}</p>
                    <p className="mt-1 truncate text-[11px] text-slate-500">{report.title}</p>
                  </div>
                  <span data-testid="right-panel-nlm-artifact-status" role="status" aria-live="polite" aria-label={`상태 ${status.label}`} className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[10px] ${status.className}`}>
                    <StatusIcon aria-hidden="true" className="h-3 w-3" />{status.label}
                  </span>
                </div>
                {artifact.status === 'completed' && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mt-2 h-7 gap-1 rounded-lg px-2 text-xs"
                    aria-label={`${artifactLabel} \ubcf4\uae30`}
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

      <section data-testid="right-panel-recent-section" role="region" aria-labelledby="right-panel-recent-title" className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
        <div id="right-panel-recent-title" className="flex items-center gap-2 text-sm font-semibold text-slate-950"><FileText className="h-4 w-4 text-indigo-600" /> 최근 결과</div>
        <div data-testid="right-panel-recent-list" role="list" className="mt-3 space-y-2">
          {latest.length === 0 ? <p className="text-xs text-slate-500">아직 생성된 결과가 없습니다.</p> : latest.map((report) => {
            const styleLabel = getStyleLabel(report.style);
            return (
              <div key={report.id} data-testid="right-panel-recent-item" role="listitem">
                <button
                  type="button"
                  data-testid="right-panel-recent-result"
                  aria-label={`${report.title} ${styleLabel} 결과 열기`}
                  className="w-full rounded-2xl bg-slate-50 p-3 text-left transition hover:bg-indigo-50"
                  onClick={() => focusReport(report.id)}
                >
                  <p className="line-clamp-2 text-xs font-medium text-slate-800">{report.title}</p>
                  <p className="mt-1 text-[11px] text-slate-500">{styleLabel}</p>
                </button>
              </div>
            );
          })}
        </div>
      </section>
      <button
        type="button"
        data-testid="right-panel-schedule-card" aria-label={scheduleLabel}
        className="rounded-3xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-indigo-200 hover:bg-indigo-50/40"
        onClick={() => setActiveView('calendar')}
      >
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-950"><CalendarDays className="h-4 w-4 text-indigo-600" /> 예약</div>
        <p className="mt-2 text-xs text-slate-500">예약된 발행 {schedulesCount}개</p>
        <p className="mt-2 text-[11px] font-medium text-indigo-600">캘린더로 이동</p>
      </button>
    </div>
  );
}
