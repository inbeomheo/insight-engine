'use client';

import { memo, useState, useMemo, useCallback, useReducer, useRef, useEffect } from 'react';
import {
  Copy, Check, ChevronDown, ChevronUp, MoreHorizontal, Trash2,
  FileText, Code, Brain, BookOpen, Share2, Pencil,
  Zap, Type, MessageSquare, ExternalLink, Layers, Mic, Bot, Headphones, ListChecks, Loader2, Image as ImageIcon,
} from 'lucide-react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// KaTeX는 수식 감지 시에만 동적 로드 (초기 번들 ~280KB 절감)
// remark-math + rehype-katex는 MathMarkdown 컴포넌트에서 조건부 import
import { toast } from 'sonner';
import type { Report, QualityScore, NlpAnalysis, ViewMode } from '@/lib/types';
import { getStyleLabel } from '@/lib/helpers';
import { useResultStore } from '@/stores/resultStore';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useTranslation } from '@/hooks/useTranslation';
import { useClipboardCopy } from '@/hooks/useClipboardCopy';
import { exportFormat, extractEvents, notebookLmGenerate, notebookLmStatus, notebookLmAuthCheck, createSharePage, createVideoDeepDiveFromResult, extractVideoDeepDiveScreenshots, createKnowledgeNote, isApiError, type NoteDuplicateWarning, type VideoDeepDiveSlide } from '@/lib/api';
import { getKnowledgeNoteContent, getKnowledgeNotePreview, getKnowledgeNoteSource } from '@/lib/knowledge-note-source';
import {
  createDownloadFilename,
  escapeHtmlText,
  getNotebookLmTerminalStatus,
  hasReportChanges,
  normalizeReportDraft,
  validateReportDraft,
  type ReportDraft,
} from '@/lib/report-edit';
import { injectTimestampLinks, markdownToHtml } from '@/lib/markdown-to-html';
import { NotebookLmSection } from './NotebookLmSection';
import ProtectedImage from '@/components/media/ProtectedImage';
import type { VideoEvent, EventSummary } from '@/lib/types';

import { ReportProvider } from './ReportContext';
import { EXPORT_HTML_STYLE } from '@/lib/exportHtmlTemplate';
import { sanitizeReportHtml } from '@/lib/sanitize-report-html';

// 조건부 서브컴포넌트 — 특정 스타일/데이터에서만 사용되므로 dynamic import
const SeoSection = dynamic(() => import('./SeoSection'), { ssr: false });
const GeoSection = dynamic(() => import('./GeoSection'), { ssr: false });
const FaqCtaSection = dynamic(() => import('./FaqCtaSection'), { ssr: false });
const FusionSections = dynamic(() => import('./FusionSections'), { ssr: false });
const ShortsClipList = dynamic(() => import('./ShortsClipList'), { ssr: false });
const WebSourcesSection = dynamic(() => import('./WebSourcesSection'), { ssr: false });
const InsertedLinksSection = dynamic(() => import('./InsertedLinksSection'), { ssr: false });
const EventTimeline = dynamic(() => import('./EventTimeline'), { ssr: false });

// 무거운 서브컴포넌트 dynamic import
const VideoChatPanel = dynamic(() => import('@/components/chat/VideoChatPanel'), { ssr: false });
const AnalysisDashboard = dynamic(() => import('./AnalysisDashboard'), { ssr: false });
const TranscriptPanel = dynamic(() => import('./TranscriptPanel'), { ssr: false });
const ChapterTimeline = dynamic(() => import('./ChapterTimeline'), { ssr: false });
const ResultChatPanel = dynamic(() => import('./ResultChatPanel'), { ssr: false });

// KaTeX 수식 렌더링 — 콘텐츠에 수식 패턴이 있을 때만 로드
const MathMarkdown = dynamic(() => import('./MathMarkdown'), { ssr: false });

// 문서 편집기 — 편집 버튼을 눌렀을 때만 필요하므로 dynamic import
const ContentEditor = dynamic(() => import('./ContentEditor'), { ssr: false });

interface ResultCardProps {
  report: Report;
  viewMode?: ViewMode;
  /** compact 모드에서 카드 클릭 시 full 전환 콜백 */
  onExpandToFull?: () => void;
}

const remarkPlugins = [remarkGfm];
const NOTEBOOKLM_ENABLED = process.env.NEXT_PUBLIC_NOTEBOOKLM_ENABLED === 'true';
const NOTEBOOKLM_POLL_INTERVAL_MS = 5000;
const NOTEBOOKLM_MAX_POLL_ATTEMPTS = 60;
const NOTEBOOKLM_MAX_CONSECUTIVE_ERRORS = 3;
const ANKI_EXPORT_STYLES = new Set(['quiz', 'retention_cards']);
// 수식 감지 패턴: $$...$$ 또는 \(...\) 또는 \[...\]
const MATH_PATTERN = /\$\$[\s\S]+?\$\$|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\]/;

function shareSnapshotFingerprint(
  report: Pick<Report, 'title' | 'content' | 'html' | 'url' | 'style'>,
): string {
  return [report.title, report.content, report.html ?? '', report.url ?? '', report.style].join('\u0000');
}

export interface NotebookLmPollJob {
  timer: ReturnType<typeof setTimeout> | null;
  cancelled: boolean;
}

interface NotebookLmPollingOptions {
  artifactId: string;
  jobs: Map<string, NotebookLmPollJob>;
  fetchStatus: (artifactId: string) => Promise<{ status: string; error?: string }>;
  onTerminal: (status: 'completed' | 'failed', error?: string) => void;
  onTimeout: () => void;
  onFailure: (error: unknown) => void;
  intervalMs?: number;
  maxAttempts?: number;
  maxConsecutiveErrors?: number;
}

function cancelNotebookLmPollJob(
  jobs: Map<string, NotebookLmPollJob>,
  artifactId: string,
  job: NotebookLmPollJob,
): void {
  job.cancelled = true;
  if (job.timer !== null) clearTimeout(job.timer);
  job.timer = null;
  if (jobs.get(artifactId) === job) jobs.delete(artifactId);
}

/**
 * NotebookLM 상태를 한 번에 하나씩 확인한다. 같은 artifact의 새 폴링이 시작되면 이전 작업은
 * 응답이 늦게 도착해도 콜백을 실행하지 못하며, 일시 오류는 연속 실패 상한까지 재시도한다.
 */
export function startNotebookLmStatusPolling({
  artifactId,
  jobs,
  fetchStatus,
  onTerminal,
  onTimeout,
  onFailure,
  intervalMs = NOTEBOOKLM_POLL_INTERVAL_MS,
  maxAttempts = NOTEBOOKLM_MAX_POLL_ATTEMPTS,
  maxConsecutiveErrors = NOTEBOOKLM_MAX_CONSECUTIVE_ERRORS,
}: NotebookLmPollingOptions): () => void {
  const previousJob = jobs.get(artifactId);
  if (previousJob) cancelNotebookLmPollJob(jobs, artifactId, previousJob);

  const job: NotebookLmPollJob = { timer: null, cancelled: false };
  jobs.set(artifactId, job);
  let attempts = 0;
  let consecutiveErrors = 0;

  const cancel = () => cancelNotebookLmPollJob(jobs, artifactId, job);
  const schedule = () => {
    if (job.cancelled) return;
    job.timer = setTimeout(() => {
      job.timer = null;
      void poll();
    }, intervalMs);
  };
  const poll = async () => {
    if (job.cancelled) return;
    if (attempts >= maxAttempts) {
      cancel();
      onTimeout();
      return;
    }
    attempts += 1;

    try {
      const status = await fetchStatus(artifactId);
      if (job.cancelled) return;
      consecutiveErrors = 0;
      const terminalStatus = getNotebookLmTerminalStatus(status.status);
      if (terminalStatus) {
        cancel();
        onTerminal(
          terminalStatus,
          status.error || (status.status === 'not_found' ? 'artifact_not_found' : undefined),
        );
        return;
      }
      schedule();
    } catch (error) {
      if (job.cancelled) return;
      consecutiveErrors += 1;
      if (consecutiveErrors >= maxConsecutiveErrors) {
        cancel();
        onFailure(error);
        return;
      }
      schedule();
    }
  };

  schedule();
  return cancel;
}

// 품질 등급별 스타일 정의
const GRADE_STYLES: Record<QualityScore['grade'], { badge: string; label: string }> = {
  A: { badge: 'border-green-500/50 text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400', label: 'A등급' },
  B: { badge: 'border-blue-500/50 text-blue-600 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-400', label: 'B등급' },
  C: { badge: 'border-yellow-500/50 text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400', label: 'C등급' },
  D: { badge: 'border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400', label: 'D등급' },
};

type VisualCue = {
  label: string;
  description: string;
};

function isVisualCueLine(line: string): boolean {
  return /^(?:[-*]\s*)?(?:\*\*)?\[?((?:사진|이미지|스크린샷)\s*\d*)\]?(?:\*\*)?\s*[:：-]\s*(.+)$/i.test(line.trim());
}

function stripTutorialVisualCueLines(content: string): string {
  return content
    .split('\n')
    .filter((line) => !isVisualCueLine(line))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function extractTutorialVisualCues(content: string): VisualCue[] {
  const seen = new Set<string>();
  return content
    .split('\n')
    .map((line) => line.trim())
    .map((line) => {
      const match = line.match(/^(?:[-*]\s*)?(?:\*\*)?\[?((?:사진|이미지|스크린샷)\s*\d*)\]?(?:\*\*)?\s*[:：-]\s*(.+)$/i);
      if (!match) return null;
      const label = match[1].trim();
      const description = match[2].replace(/\*\*/g, '').trim();
      const key = `${label}:${description}`;
      if (!description || seen.has(key)) return null;
      seen.add(key);
      return { label, description };
    })
    .filter((cue): cue is VisualCue => Boolean(cue))
    .slice(0, 7);
}

function TutorialVisualCueSection({
  cues,
  onSaveDeepDive,
  onExtractScreenshots,
  isSaving,
  isExtracting,
  deepDiveUrl,
  slides,
}: {
  cues: VisualCue[];
  onSaveDeepDive?: () => void;
  onExtractScreenshots?: () => void;
  isSaving?: boolean;
  isExtracting?: boolean;
  deepDiveUrl?: string | null;
  slides?: VideoDeepDiveSlide[];
}) {
  if (cues.length === 0 && (!slides || slides.length === 0)) return null;
  const visibleSlides = (slides || []).filter((slide) => slide.img);
  return (
    <section className="mb-5 rounded-sm border border-primary/25 bg-primary/5 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-sm border border-primary/30 bg-background text-primary">
            <ImageIcon className="h-4 w-4" />
          </span>
          <div>
            <h4 className="text-sm font-black tracking-[-0.01em] text-foreground">시각 자료 가이드</h4>
            <p className="text-xs text-muted-foreground">
              {visibleSlides.length > 0 ? '영상에서 실제 화면을 추출했어.' : '각 단계에 넣으면 좋은 사진/스크린샷 큐시트야.'}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="shrink-0 text-[10px] font-bold uppercase tracking-[0.12em] text-primary">
            {visibleSlides.length > 0 ? `${visibleSlides.length} SHOTS` : `${cues.length} CUTS`}
          </span>
          {onExtractScreenshots && (
            <Button size="sm" className="h-8 rounded-sm text-xs" onClick={onExtractScreenshots} disabled={isExtracting || isSaving}>
              {isExtracting ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <ImageIcon className="mr-1.5 h-3.5 w-3.5" />}
              {isExtracting ? '추출 중...' : '스크린샷 추출'}
            </Button>
          )}
          {deepDiveUrl ? (
            <Button asChild size="sm" variant="outline" className="h-8 rounded-sm border-primary/40 text-xs text-primary">
              <a href={deepDiveUrl} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="mr-1.5 h-3.5 w-3.5" />
                딥다이브 열기
              </a>
            </Button>
          ) : onSaveDeepDive ? (
            <Button size="sm" variant="outline" className="h-8 rounded-sm border-primary/40 text-xs text-primary" onClick={onSaveDeepDive} disabled={isSaving || isExtracting}>
              {isSaving ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <ImageIcon className="mr-1.5 h-3.5 w-3.5" />}
              딥다이브 저장
            </Button>
          ) : null}
        </div>
      </div>

      {visibleSlides.length > 0 && (
        <div className="mb-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {visibleSlides.slice(0, 6).map((slide, index) => (
            <figure key={`${slide.img}-${index}`} className="overflow-hidden rounded-sm border border-border/70 bg-card">
              <ProtectedImage src={slide.img} alt={slide.title || `스크린샷 ${index + 1}`} className="aspect-video w-full object-cover" />
              <figcaption className="flex items-center justify-between gap-2 px-3 py-2 text-xs text-muted-foreground">
                <span className="font-semibold text-primary">{slide.mmss || '00:00'}</span>
                <span className="truncate">{slide.title || `스크린샷 ${index + 1}`}</span>
              </figcaption>
            </figure>
          ))}
        </div>
      )}

      <div className="grid gap-2 sm:grid-cols-2">
        {cues.map((cue, index) => (
          <div key={`${cue.label}-${index}`} className="rounded-sm border border-border/70 bg-card p-3">
            <div className="mb-1 text-[10px] font-bold uppercase tracking-[0.12em] text-primary">{cue.label || `사진 ${index + 1}`}</div>
            <p className="text-sm leading-6 text-foreground/85">{cue.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

// 패널 상태 리듀서 — 13개 useState → 단일 리듀서 (상태 변경 시 1회 리렌더)
interface PanelState {
  collapsed: boolean;
  hasExpanded: boolean;
  chatOpen: boolean;
  showTranscript: boolean;
  eventOpen: boolean;
  eventLoading: boolean;
  extractedEvents: VideoEvent[] | null;
  eventSummary: EventSummary | null;
}
type PanelAction =
  | { type: 'SET'; key: keyof PanelState; value: PanelState[keyof PanelState] }
  | { type: 'BATCH'; updates: Partial<PanelState> };

const panelInitial: PanelState = {
  collapsed: false, hasExpanded: true,
  chatOpen: false, showTranscript: false,
  eventOpen: false, eventLoading: false, extractedEvents: null, eventSummary: null,
};

function panelReducer(state: PanelState, action: PanelAction): PanelState {
  if (action.type === 'SET') {
    if (state[action.key] === action.value) return state;
    return { ...state, [action.key]: action.value };
  }
  // BATCH: 여러 상태를 한 번에 업데이트 (리렌더 1회)
  return { ...state, ...action.updates };
}

const ResultCard = memo(function ResultCard({ report, viewMode = 'full', onExpandToFull }: ResultCardProps) {
  const router = useRouter();
  const [panel, dispatch] = useReducer(panelReducer, panelInitial);
  const [isSharing, setIsSharing] = useState(false);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [isSavingDeepDive, setIsSavingDeepDive] = useState(false);
  const [isExtractingScreenshots, setIsExtractingScreenshots] = useState(false);
  const [deepDiveUrl, setDeepDiveUrl] = useState<string | null>(null);
  const [deepDiveSlides, setDeepDiveSlides] = useState<VideoDeepDiveSlide[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const { collapsed, hasExpanded, chatOpen, showTranscript, eventOpen, eventLoading, extractedEvents, eventSummary } = panel;

  // 간편 setter
  const setPanel = useCallback(<K extends keyof PanelState>(key: K, value: PanelState[K]) => {
    dispatch({ type: 'SET', key, value });
  }, []);

  // Zustand selector — 함수 참조만 구독 (전체 스토어 구독 방지)
  const removeReport = useResultStore((s) => s.removeReport);
  const updateReport = useResultStore((s) => s.updateReport);
  const updateReportPersisted = useResultStore((s) => s.updateReportPersisted);
  const setPromptModalOpen = useUIStore((s) => s.setPromptModalOpen);

  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const noteLanguage = useSettingsStore((s) => s.modifiers.language ?? 'ko');
  const { t } = useTranslation();
  const {
    status: copyStatus,
    activeKey: copyKey,
    copyText: copyClipboardText,
    copyItems: copyClipboardItems,
  } = useClipboardCopy();
  const copiedField = copyStatus === 'copied' ? copyKey : null;
  const noteSource = getKnowledgeNoteSource(report);
  const notePreview = useMemo(() => (noteSource ? getKnowledgeNotePreview(report) : null), [noteSource, report]);
  const linkedNoteId = report.knowledge_note_id;
  // 스트림이 실제로 갱신 중인 임시 보고서만 편집을 막는다.
  // 완료된 마크다운/평문 결과는 html이 비어 있어도 편집할 수 있어야 한다.
  const isStreaming = report.is_streaming === true;
  const editingBaseRef = useRef<string | null>(null);
  const canExportAnki = ANKI_EXPORT_STYLES.has(report.style);

  // NotebookLM 폴링 작업 추적 — 언마운트 시 타이머와 진행 중 응답을 모두 무효화한다.
  const pollJobsRef = useRef<Map<string, NotebookLmPollJob>>(new Map());
  useEffect(() => {
    const jobs = pollJobsRef.current;
    return () => {
      jobs.forEach((job, artifactId) => cancelNotebookLmPollJob(jobs, artifactId, job));
      jobs.clear();
    };
  }, []);

  const charCount = report.content.length;

  // --- 문서 편집 (제목 + 본문 마크다운) ---
  // 저장 성공 알림 전에 resultStore.updateReportPersisted로 localStorage 기록을 끝낸다.
  const startEditing = useCallback(() => {
    if (isStreaming) {
      toast.info(t('result.editStreaming'));
      return;
    }
    if (isSharing) {
      toast.info(t('result.shareInProgress'));
      return;
    }
    editingBaseRef.current = `${report.title}\u0000${report.content}`;
    dispatch({ type: 'BATCH', updates: { hasExpanded: true, collapsed: false } });
    setIsEditing(true);
  }, [isSharing, isStreaming, report.title, report.content, t]);

  const handleSaveEdit = useCallback(
    async (draft: ReportDraft) => {
      const currentFingerprint = `${report.title}\u0000${report.content}`;
      if (isStreaming || editingBaseRef.current !== currentFingerprint) {
        toast.error(t(isStreaming ? 'result.editStreaming' : 'result.editConflict'));
        return;
      }
      const error = validateReportDraft(draft);
      if (error) {
        toast.error(t(`result.${error === 'emptyTitle' ? 'editEmptyTitle' : 'editEmptyContent'}`));
        return;
      }
      if (!hasReportChanges(report, draft)) {
        editingBaseRef.current = null;
        setIsEditing(false);
        toast.info(t('result.editNoChange'));
        return;
      }
      const { title, content } = normalizeReportDraft(draft);
      // html은 내보내기/공유가 소비하므로 편집 본문으로 다시 렌더링해 stale 상태를 막는다.
      try {
        const html = await markdownToHtml(content, report.url);
        // 기존 공유 페이지는 편집 전 스냅샷이므로 편집 저장과 같은 트랜잭션에서 무효화한다.
        const saved = updateReportPersisted(report.id, { title, content, html, share_url: undefined });
        if (!saved) {
          toast.error(t('result.editStorageFailed'));
          return;
        }
        editingBaseRef.current = null;
        setIsEditing(false);
        toast.success(t('result.editSaved'));
      } catch {
        toast.error(t('result.editSaveFailed'));
      }
    },
    [report, updateReportPersisted, t, isStreaming],
  );

  const cancelEditing = useCallback(() => {
    editingBaseRef.current = null;
    setIsEditing(false);
  }, []);

  const tokenMeta = `${(report.usage?.total_tokens ?? 0).toLocaleString()} TOKENS`;
  const timeMeta = `${(report.elapsed_time ?? 0).toFixed(1)}초`;

  async function copyText(text: string, field: string) {
    const result = await copyClipboardText(text, field);
    if (!result.isCurrent) return result;
    if (result.copied) toast.success(t('result.copied'));
    else toast.error(t('result.copyFailed'));
    return result;
  }

  async function copyRich() {
    const result = await copyClipboardItems(async () => {
      const rendered = report.html || await markdownToHtml(report.content, report.url);
      const html = sanitizeReportHtml(rendered);
      const blob = new Blob([html], { type: 'text/html' });
      const textBlob = new Blob([report.content], { type: 'text/plain' });
      return [
        new ClipboardItem({
          'text/html': blob,
          'text/plain': textBlob,
        }),
      ];
    }, 'rich');

    if (!result.isCurrent) return;
    if (result.copied) {
      toast.success(t('result.richCopied'));
    } else {
      await copyText(report.content, 'content');
    }
  }

  async function handleExportHtml() {
    const rendered = report.html || await markdownToHtml(report.content, report.url);
    const html = `<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>${escapeHtmlText(report.title)}</title>
<style>${EXPORT_HTML_STYLE}</style></head><body>${sanitizeReportHtml(rendered)}</body></html>`;
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = createDownloadFilename(report.title, 'html');
    a.click();
    URL.revokeObjectURL(url);
    toast.success(t('result.htmlSuccess'));
  }

  async function handleShare() {
    if (isSharing || isEditing) return;
    const snapshotFingerprint = shareSnapshotFingerprint(report);
    setIsSharing(true);
    try {
      let shareUrl = report.share_url ?? '';
      let shareError: unknown;
      const result = await copyClipboardText(async () => {
        try {
          if (!shareUrl) {
            const rendered = report.html || await markdownToHtml(report.content, report.url);
            const createdShareUrl = (await createSharePage({
              title: report.title,
              content: report.content,
              html: rendered,
              url: report.url,
              style: report.style,
            })).share_url;

            // 공유 페이지는 요청 시점의 스냅샷이다. 요청 중 다른 화면/동기화가
            // 문서를 편집했다면 오래된 URL을 최신 보고서에 다시 연결하지 않는다.
            const latestReport = useResultStore.getState().reports.find(
              (item) => item.id === report.id,
            );
            if (
              !latestReport
              || shareSnapshotFingerprint(latestReport) !== snapshotFingerprint
            ) {
              throw new Error(t('result.shareStale'));
            }

            shareUrl = createdShareUrl;
            updateReport(report.id, { share_url: shareUrl });
          }
          return shareUrl;
        } catch (error) {
          shareError = error;
          throw error;
        }
      }, 'share');

      if (shareError) {
        const message = shareError instanceof Error
          ? shareError.message
          : '공유 링크 생성 실패';
        toast.error(message);
        return;
      }
      if (!result.isCurrent) return;
      if (!result.copied) {
        toast.error(t('result.copyFailed'));
        return;
      }
      toast.success(t('result.shareCopied'), {
        description: shareUrl,
      });
    } finally {
      setIsSharing(false);
    }
  }

  function openKnowledgeNote(noteId: string) {
    router.push(`/notes/${encodeURIComponent(noteId)}`);
  }

  function markKnowledgeNoteLinked(noteId: string, title?: string) {
    updateReport(report.id, {
      knowledge_note_id: noteId,
      knowledge_note_title: title || noteSource?.title || '학습 노트',
      knowledge_note_saved_at: new Date().toISOString(),
    });
  }

  async function handleSaveKnowledgeNote() {
    if (isSavingNote || !noteSource) return;
    setIsSavingNote(true);
    try {
      const note = await createKnowledgeNote({
        content: getKnowledgeNoteContent(report),
        language: noteLanguage,
        model: selectedModel || undefined,
        source: noteSource,
      });
      markKnowledgeNoteLinked(note.id, note.source?.title);
      toast.success('학습 노트로 저장했습니다.', {
        description: '핵심 개념·인용·복습 질문으로 지식위키에 추가했습니다.',
        action: {
          label: '열기',
          onClick: () => {
            openKnowledgeNote(note.id);
          },
        },
      });
    } catch (err) {
      const body = isApiError<NoteDuplicateWarning>(err) ? err.body : undefined;
      const duplicate = body?.duplicate_notes?.[0];
      if (isApiError<NoteDuplicateWarning>(err) && err.status === 409 && duplicate?.id) {
        markKnowledgeNoteLinked(duplicate.id, duplicate.title);
        toast.warning(body?.warning || '이미 학습한 자료와 비슷합니다.', {
          description: body?.next_action || '기존 노트를 열어 이어서 확인하세요.',
          action: {
            label: '기존 노트 열기',
            onClick: () => {
              openKnowledgeNote(duplicate.id);
            },
          },
        });
      } else {
        toast.error(err instanceof Error ? err.message : '학습 노트 저장에 실패했습니다.');
      }
    } finally {
      setIsSavingNote(false);
    }
  }

  function handleKnowledgeNoteAction() {
    if (linkedNoteId) {
      openKnowledgeNote(linkedNoteId);
      return;
    }
    void handleSaveKnowledgeNote();
  }

  async function handleExportFormat(format: 'markdown' | 'anki') {
    try {
      const blob = await exportFormat(format, report.title, report.content, {
        style: report.style,
        source_url: report.url,
        tags: [report.style, 'generated-content'],
      });
      const ext = format === 'markdown' ? 'md' : 'apkg';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = createDownloadFilename(report.title, ext);
      a.click();
      URL.revokeObjectURL(url);
      toast.success(format === 'anki' ? 'Anki 덱 내보내기 완료' : 'MD 내보내기 완료');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '내보내기에 실패했습니다.');
    }
  }

  async function handleNotebookLm(contentType: string) {
    const auth = await notebookLmAuthCheck().catch(() => null);
    if (!auth?.valid) {
      toast.error('NotebookLM 인증이 필요합니다. 터미널에서 nlm login을 실행해주세요.');
      return;
    }
    const sourceText = report.transcript || report.content;
    try {
      const res = await notebookLmGenerate({
        type: contentType,
        url: report.url,
        source_text: sourceText,
      });
      const artifact = { artifact_id: res.artifact_id, content_type: contentType, status: 'in_progress' as const };
      const latestReport = useResultStore.getState().reports.find((item) => item.id === report.id);
      const existing = latestReport?.notebooklm?.artifacts ?? report.notebooklm?.artifacts ?? [];
      const artifacts = [...existing.filter((item) => item.artifact_id !== artifact.artifact_id), artifact];
      updateReport(report.id, { notebooklm: { artifacts } });
      toast.success(`NotebookLM ${contentType} 생성 시작`);

      const finishArtifact = (status: 'completed' | 'failed', error?: string) => {
        const currentReport = useResultStore.getState().reports.find((item) => item.id === report.id);
        const currentArtifacts = currentReport?.notebooklm?.artifacts ?? [...existing, artifact];
        const hasArtifact = currentArtifacts.some((item) => item.artifact_id === artifact.artifact_id);
        const artifacts = (hasArtifact ? currentArtifacts : [...currentArtifacts, artifact]).map((item) =>
          item.artifact_id === artifact.artifact_id ? { ...item, status, ...(error ? { error } : {}) } : item,
        );
        updateReport(report.id, { notebooklm: { artifacts } });
      };

      startNotebookLmStatusPolling({
        artifactId: res.artifact_id,
        jobs: pollJobsRef.current,
        fetchStatus: notebookLmStatus,
        onTerminal: (terminalStatus, error) => {
          finishArtifact(terminalStatus, error);
          if (terminalStatus === 'completed') toast.success(`NotebookLM ${contentType} 생성 완료!`);
          else toast.error(`NotebookLM ${contentType} 생성 실패`);
        },
        onTimeout: () => {
          finishArtifact('failed', 'status_poll_timeout');
          toast.error(`NotebookLM ${contentType} 생성 상태 확인 시간이 초과되었습니다.`);
        },
        onFailure: (error) => {
          finishArtifact('failed', error instanceof Error ? error.message : 'status_check_failed');
          toast.error(`NotebookLM ${contentType} 상태 확인에 반복해서 실패했습니다.`);
        },
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'NotebookLM 생성에 실패했습니다.');
    }
  }

  async function handleExtractEvents() {
    // 이미 추출된 경우 패널 토글만
    if (extractedEvents !== null) {
      setPanel('eventOpen', !eventOpen);
      return;
    }

    dispatch({ type: 'BATCH', updates: { eventLoading: true, eventOpen: true } });

    try {
      const res = await extractEvents({
        url: report.url,
        transcript: report.transcript,
      });
      dispatch({ type: 'BATCH', updates: { extractedEvents: res.events, eventSummary: res.summary } });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '이벤트 추출에 실패했습니다.');
      setPanel('eventOpen', false);
    } finally {
      setPanel('eventLoading', false);
    }
  }

  function getReportVideoId(): string | null {
    const source = report.url || '';
    const match = source.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([\w-]{11})/);
    return match?.[1] ?? null;
  }

  async function handleSaveDeepDive() {
    const videoId = getReportVideoId();
    if (!videoId) {
      toast.error('YouTube 영상 URL이 있는 결과에서만 딥다이브를 만들 수 있어.');
      return;
    }
    setIsSavingDeepDive(true);
    try {
      const res = await createVideoDeepDiveFromResult({
        video_id: videoId,
        source_url: report.url,
        title: report.youtube_title || report.title,
        content: report.content,
        transcript: report.transcript,
        transcript_segments: report.transcript_segments,
      });
      setDeepDiveUrl(res.viewer_url);
      toast.success('사진 가이드를 딥다이브로 저장했어.');
      if (typeof window !== 'undefined') {
        window.open(res.viewer_url, '_blank', 'noopener,noreferrer');
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '딥다이브 저장에 실패했습니다.');
    } finally {
      setIsSavingDeepDive(false);
    }
  }

  async function handleExtractScreenshots() {
    const videoId = getReportVideoId();
    if (!videoId) {
      toast.error('YouTube 영상 URL이 있는 결과에서만 스크린샷을 추출할 수 있어.');
      return;
    }
    setIsExtractingScreenshots(true);
    try {
      toast.info('영상 화면을 추출하는 중이야. 영상 길이에 따라 1~5분 걸릴 수 있어.');
      const res = await extractVideoDeepDiveScreenshots({
        video_id: videoId,
        url: report.url,
        title: report.youtube_title || report.title,
        content: report.content,
        transcript: report.transcript,
        max_slides: Math.min(Math.max(tutorialVisualCues.length || 6, 4), 8),
        scene_threshold: 0.24,
        min_gap: 8,
      });
      setDeepDiveSlides(res.slides || res.meta.slides || []);
      setDeepDiveUrl(res.viewer_url);
      toast.success(`스크린샷 ${res.meta.slide_count || res.slides?.length || 0}장을 추출했어.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '스크린샷 추출에 실패했습니다.');
    } finally {
      setIsExtractingScreenshots(false);
    }
  }

  const articleContent = useMemo(
    () => ['tutorial', 'course'].includes(report.style) ? stripTutorialVisualCueLines(report.content) : report.content,
    [report.style, report.content],
  );

  // ReactMarkdown은 비싸므로 스트리밍 완료 후에만 렌더링
  const processedContent = useMemo(
    () => isStreaming ? articleContent : injectTimestampLinks(articleContent, report.url),
    [isStreaming, articleContent, report.url],
  );

  const hasMath = useMemo(() => MATH_PATTERN.test(processedContent), [processedContent]);
  const tutorialVisualCues = useMemo(
    () => ['tutorial', 'course'].includes(report.style) ? extractTutorialVisualCues(report.content) : [],
    [report.style, report.content],
  );

  const markdownBody = useMemo(
    () => isStreaming ? (
      <div className="whitespace-pre-wrap">{processedContent}</div>
    ) : hasMath ? (
      <MathMarkdown content={processedContent} remarkPlugins={remarkPlugins} />
    ) : (
      <ReactMarkdown remarkPlugins={remarkPlugins}>
        {processedContent}
      </ReactMarkdown>
    ),
    [isStreaming, processedContent, hasMath],
  );
  const chatContext = useMemo(
    () => report.transcript || report.content,
    [report.transcript, report.content],
  );

  // --- Compact 모드: 요약 카드 ---
  if (viewMode === 'compact') {
    const preview = report.content.slice(0, 100) + (report.content.length > 100 ? '…' : '');
    return (
      <ReportProvider report={report}>
      <Card
        className="overflow-hidden rounded-sm border-border bg-card shadow-none transition-colors hover:border-primary/40 cursor-pointer"
        onClick={onExpandToFull}
      >
        <div className="px-4 py-3">
          {/* 메타 칩 + 제목 */}
          <div className="flex items-center gap-2 mb-1">
            <span className="signal-meta text-[10px] text-muted-foreground/70 font-medium">
              {getStyleLabel(report.style)}
            </span>
            <span className="signal-meta text-[10px] text-muted-foreground">{report.time}</span>
            <span className="signal-meta ml-auto text-[10px] text-muted-foreground inline-flex items-center gap-1">
              <Zap className="h-3 w-3" />
              {(report.usage?.total_tokens ?? 0).toLocaleString()} · {(report.elapsed_time ?? 0).toFixed(1)}초
            </span>
          </div>
          <h3 className="font-semibold text-sm leading-snug tracking-tight truncate">{report.title}</h3>
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{preview}</p>
        </div>
      </Card>
      </ReportProvider>
    );
  }

  return (
    <ReportProvider report={report}>
    <>
    {chatOpen && report.url && (
      <VideoChatPanel
        videoUrl={report.url}
        videoTitle={report.youtube_title || report.title}
        model={selectedModel || undefined}
        onClose={() => setPanel('chatOpen', false)}
      />
    )}
    <Card className="mx-auto max-w-[920px] overflow-hidden rounded-sm border-border bg-card shadow-none transition-colors hover:border-primary/40">
      {/* 헤더 */}
      <div className="px-6 pt-6 pb-3 lg:px-8 xl:px-10">
        {/* 뱃지 + 액션 */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="signal-meta text-[10px] font-semibold text-primary">
              {getStyleLabel(report.style)}
            </span>
            <span className="signal-meta text-[10px] text-muted-foreground">{report.time}</span>
            {report.merged && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-primary/40 text-primary">
                <Layers className="h-3 w-3 mr-1" />
                통합
              </Badge>
            )}
            {report.isFusion && (
              <Badge variant="outline" className="text-xs border-purple-400/40 text-purple-500">
                퓨전
              </Badge>
            )}
            {report.cached && (
              <Badge variant="outline" className="text-xs">캐시</Badge>
            )}
            {report.transcript_source === 'whisper' && (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground/60">
                <Mic className="h-3 w-3" />
                음성인식
              </span>
            )}
            {report.comment_summary_included && (
              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground/60">
                <MessageSquare className="h-3 w-3" />
                댓글
              </span>
            )}
            {report.quality_score && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="outline"
                    className={`text-[10px] px-1.5 py-0 cursor-default ${GRADE_STYLES[report.quality_score.grade].badge}`}
                  >
                    품질 {GRADE_STYLES[report.quality_score.grade].label}
                  </Badge>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-xs">
                  <div className="space-y-1 text-xs">
                    <div className="font-medium mb-1">품질 평가 세부 점수</div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
                      <span>정확성</span><span className="font-mono">{report.quality_score.accuracy}/10</span>
                      <span>일관성</span><span className="font-mono">{report.quality_score.coherence}/10</span>
                      <span>가독성</span><span className="font-mono">{report.quality_score.readability}/10</span>
                      <span>유용성</span><span className="font-mono">{report.quality_score.usefulness}/10</span>
                      <span className="font-medium">종합</span><span className="font-mono font-medium">{report.quality_score.overall}/10</span>
                    </div>
                    <div className="mt-1.5 pt-1.5 border-t border-border/50 text-muted-foreground leading-snug">
                      {report.quality_score.feedback}
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            {report.transcript_segments && report.transcript_segments.length > 0 && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 rounded-sm"
                    onClick={() => setPanel('showTranscript', !showTranscript)}
                  >
                    <FileText className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>{showTranscript ? '요약 보기' : '자막 보기'}</TooltipContent>
              </Tooltip>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={report.share_url ? 'secondary' : 'outline'}
                  size="sm"
                  className="signal-meta h-8 gap-1.5 rounded-sm border-primary/40 px-2.5 text-[10px] text-primary hover:bg-primary/5"
                  onClick={handleShare}
                  disabled={isSharing || isEditing}
                  aria-label={report.share_url ? '공유 링크 복사' : '공유 페이지 만들고 링크 복사'}
                >
                  {isSharing ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : copiedField === 'share' ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : (
                    <Share2 className="h-3.5 w-3.5" />
                  )}
                  <span className="hidden sm:inline">{report.share_url ? '링크 복사' : '공유'}</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>{report.share_url ? '공유 링크만 복사' : '공유 페이지 생성 후 URL만 복사'}</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 rounded-sm"
                  onClick={copyRich}
                >
                  {copiedField === 'rich' ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Type className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{t('result.richCopy')}</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={isEditing ? 'secondary' : 'ghost'}
                  size="icon"
                  className="h-8 w-8 rounded-sm"
                  aria-label={t('result.edit')}
                  aria-pressed={isEditing}
                  disabled={isStreaming || isSharing}
                  onClick={() => (isEditing ? cancelEditing() : startEditing())}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{t(isStreaming ? 'result.editStreaming' : 'result.edit')}</TooltipContent>
            </Tooltip>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-sm"
              aria-label={collapsed ? '카드 펼치기' : '카드 접기'}
              aria-expanded={!collapsed}
              onClick={() => {
                if (collapsed) {
                  dispatch({ type: 'BATCH', updates: { hasExpanded: true, collapsed: false } });
                } else {
                  setPanel('collapsed', true);
                }
              }}
            >
              {collapsed ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronUp className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>

        {/* 제목 */}
        <div className="signal-meta mb-2 text-[10px] text-muted-foreground/70">
          {report.time} · {tokenMeta} · {timeMeta} · {charCount.toLocaleString()}자
        </div>
        <h3 className="max-w-none text-[26px] font-bold leading-tight tracking-[-0.02em] text-foreground sm:text-[34px]">{report.title}</h3>

        {/* 소스 링크 */}
        {report.merged && report.source_videos ? (
          <div className="flex flex-col gap-1 mt-1.5">
            {report.source_videos.map((sv, i) => (
              <a
                key={sv.url}
                href={sv.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
              >
                <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{t('result.sourceVideo', { index: i + 1 })}: {sv.title}</span>
              </a>
            ))}
          </div>
        ) : report.url ? (
          <a
            href={report.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline mt-1.5"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            {report.youtube_title || t('result.originalVideo')}
          </a>
        ) : null}
      </div>

      {/* 본문 — 한번 펼치면 DOM 유지 + display:none으로만 숨김 → 토글 즉시 반응 */}
      {hasExpanded && (
      <CardContent className="border-t border-border/50 px-6 pb-6 pt-5 lg:px-8 xl:px-10" style={{ display: collapsed ? 'none' : undefined }}>
          {tutorialVisualCues.length > 0 && (
            <TutorialVisualCueSection
              cues={tutorialVisualCues}
              onSaveDeepDive={report.url ? handleSaveDeepDive : undefined}
              onExtractScreenshots={report.url ? handleExtractScreenshots : undefined}
              isSaving={isSavingDeepDive}
              isExtracting={isExtractingScreenshots}
              deepDiveUrl={deepDiveUrl}
              slides={deepDiveSlides}
            />
          )}

          {notePreview && !linkedNoteId && (
            <section className="mb-5 rounded-sm border border-primary/25 bg-primary/5 p-4">
              <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="mb-1 flex items-center gap-2 text-sm font-black text-foreground">
                    <BookOpen className="h-4 w-4 text-primary" />
                    학습 노트 미리보기
                  </div>
                  <p className="text-xs leading-5 text-muted-foreground">
                    저장하면 지식위키에 아래 구조로 추가됩니다. 태그와 핵심 개념은 저장 전 검토용입니다.
                  </p>
                </div>
                <Button
                  size="sm"
                  className="h-8 rounded-sm text-xs"
                  onClick={handleKnowledgeNoteAction}
                  disabled={isSavingNote}
                >
                  {isSavingNote ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <BookOpen className="mr-1.5 h-3.5 w-3.5" />}
                  {isSavingNote ? '저장 중...' : '노트로 저장'}
                </Button>
              </div>
              <div className="mb-3 flex flex-wrap gap-1.5">
                {notePreview.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-[10px]">
                    {tag}
                  </Badge>
                ))}
                <Badge variant="outline" className="text-[10px]">
                  {notePreview.contentChars.toLocaleString()}자
                </Badge>
              </div>
              {notePreview.concepts.length > 0 && (
                <div className="mb-3 flex flex-wrap gap-1.5">
                  {notePreview.concepts.map((concept) => (
                    <span key={concept} className="rounded-full border border-primary/20 bg-background px-2 py-0.5 text-[11px] font-semibold text-primary">
                      {concept}
                    </span>
                  ))}
                </div>
              )}
              <div className="grid gap-2 md:grid-cols-2">
                {notePreview.learningPoints.slice(0, 2).map((point, index) => (
                  <p key={`${point}-${index}`} className="rounded-sm border border-border/70 bg-card p-2.5 text-xs leading-5 text-foreground/80">
                    {point}
                  </p>
                ))}
              </div>
            </section>
          )}

          {/* 편집 모드: 뷰 모드/자막 패널 대신 편집기를 표시 */}
          {isEditing ? (
            <ContentEditor
              initialTitle={report.title}
              initialContent={report.content}
              onSave={handleSaveEdit}
              onCancel={cancelEditing}
            />
          ) : viewMode === 'timeline' && report.chapters && report.chapters.length > 0 ? (
            <>
              {/* 타임라인 모드: 챕터 우선 표시 + 챕터별 콘텐츠 */}
              <ChapterTimeline chapters={report.chapters} videoUrl={report.url} />
              <div className="mt-5 space-y-4">
                {report.chapters.map((ch, i) => (
                  <div key={i} className="border-l-2 border-primary/30 pl-4">
                    <h4 className="text-sm font-semibold mb-1">{ch.title}</h4>
                    <p className="text-sm text-muted-foreground leading-relaxed">{ch.summary}</p>
                  </div>
                ))}
              </div>
              {/* 타임라인 모드에서도 전체 콘텐츠 접기 가능하도록 표시 */}
              <details className="mt-5">
                <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                  전체 콘텐츠 보기
                </summary>
                <div className="prose max-w-none text-[15.5px] leading-[1.75] text-foreground/90 mt-3">
                  {markdownBody}
                </div>
              </details>
            </>
          ) : viewMode === 'timeline' ? (
            <>
              {/* 챕터 데이터 없음 — Full 모드로 폴백 */}
              <div className="text-xs text-muted-foreground mb-3 px-3 py-2 bg-muted/30 rounded-md">
                이 콘텐츠에는 챕터 데이터가 없어 전체 보기로 표시합니다.
              </div>
              {showTranscript && report.transcript_segments && report.transcript_segments.length > 0 ? (
                <TranscriptPanel
                  segments={report.transcript_segments}
                  videoId={report.url?.match(/(?:v=|youtu\.be\/)([^&]+)/)?.[1]}
                />
              ) : (
                <div className="prose max-w-none text-[15.5px] leading-[1.75] text-foreground/90">
                  {markdownBody}
                </div>
              )}
            </>
          ) : (
            <>
              {showTranscript && report.transcript_segments && report.transcript_segments.length > 0 ? (
                <TranscriptPanel
                  segments={report.transcript_segments}
                  videoId={report.url?.match(/(?:v=|youtu\.be\/)([^&]+)/)?.[1]}
                />
              ) : (
                <div className="prose max-w-none text-[15.5px] leading-[1.75] text-foreground/90">
                  {markdownBody}
                </div>
              )}

              {/* 챕터 타임라인 (full 모드에서만 기존 위치에 표시) */}
              {report.chapters && report.chapters.length > 0 && (
                <ChapterTimeline chapters={report.chapters} videoUrl={report.url} />
              )}
            </>
          )}

          <ResultChatPanel
            context={chatContext}
            model={selectedModel || undefined}
            language="ko"
          />

          {/* NotebookLM 섹션 */}
          {report.notebooklm?.artifacts && (
            <NotebookLmSection artifacts={report.notebooklm.artifacts} />
          )}

          {/* SEO 섹션 */}
          {report.seo && <SeoSection seo={report.seo} />}

          {/* GEO 섹션 */}
          {report.geo && (
            <GeoSection
              geo={report.geo}
              cta={report.cta}
              json_ld_schemas={report.json_ld_schemas}
            />
          )}

          {/* FAQ + CTA 섹션 (기존 결과 호환) */}
          {(report.faq_schema || report.cta) && (
            <FaqCtaSection faqSchema={report.faq_schema} cta={report.cta} content={report.content} />
          )}

          {/* Shorts 클립 섹션 */}
          {report.style === 'shorts_script' && report.shorts_clips && (
            <ShortsClipList clips={report.shorts_clips} />
          )}

          {/* 퓨전 섹션 */}
          {report.isFusion && (
            <FusionSections sections={report.sections} fusionMeta={report.fusionMeta} />
          )}

          {/* NLP 분석 섹션 */}
          {report.analysis && <NlpAnalysisSection analysis={report.analysis} />}

          {/* 웹 검색 출처 섹션 */}
          {report.web_sources && report.web_sources.length > 0 && (
            <WebSourcesSection sources={report.web_sources} />
          )}

          {/* SEO 자동 삽입 링크 섹션 */}
          {report.inserted_links && report.inserted_links.length > 0 && (
            <InsertedLinksSection links={report.inserted_links} />
          )}

          {/* 이벤트 타임라인 */}
          {eventOpen && (
            <div className="mt-5 border border-border/50 rounded-lg overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 bg-muted/30 border-b border-border/30">
                <span className="flex items-center gap-2 text-sm font-medium">
                  <ListChecks className="h-4 w-4" />
                  이벤트 추출
                </span>
                <button
                  type="button"
                  onClick={() => setPanel('eventOpen', false)}
                  aria-label="이벤트 패널 닫기"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  닫기
                </button>
              </div>
              <div className="p-4">
                {eventLoading ? (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    이벤트를 분석 중입니다...
                  </p>
                ) : extractedEvents ? (
                  <EventTimeline
                    events={extractedEvents}
                    summary={eventSummary ?? undefined}
                    videoUrl={report.url}
                  />
                ) : null}
              </div>
            </div>
          )}
        </CardContent>
      )}

      {/* 푸터 */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/50 px-6 py-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Zap className="h-3 w-3" />
          {(report.usage?.total_tokens ?? 0).toLocaleString()} tokens · {(report.elapsed_time ?? 0).toFixed(1)}초 · {charCount.toLocaleString()}자
        </span>

        <div className="flex items-center gap-0.5">
          {/* 더보기 메뉴 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="더보기 메뉴" aria-haspopup="menu">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem
                onClick={startEditing}
                disabled={isStreaming || isSharing}
              >
                <Pencil className="h-3.5 w-3.5 mr-2" />
                {t('result.edit')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => copyText(report.title, 'title')}>
                <Copy className="h-3.5 w-3.5 mr-2" />
                {t('result.copyTitle')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => copyText(report.content, 'content')}>
                <FileText className="h-3.5 w-3.5 mr-2" />
                {t('result.copyAll')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setPromptModalOpen(true, report.prompt)}>
                <Code className="h-3.5 w-3.5 mr-2" />
                {t('result.promptView')}
              </DropdownMenuItem>
              {(noteSource || linkedNoteId) && (
                <DropdownMenuItem onClick={handleKnowledgeNoteAction} disabled={!linkedNoteId && isSavingNote}>
                  {!linkedNoteId && isSavingNote ? (
                    <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />
                  ) : (
                    <BookOpen className="h-3.5 w-3.5 mr-2" />
                  )}
                  {linkedNoteId ? '학습 노트 열기' : isSavingNote ? '노트 저장 중...' : '학습 노트로 저장'}
                </DropdownMenuItem>
              )}
              {NOTEBOOKLM_ENABLED && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => handleNotebookLm('audio')}>
                    <Headphones className="h-3.5 w-3.5 mr-2" />
                    NLM 팟캐스트
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleNotebookLm('video')}>
                    <Layers className="h-3.5 w-3.5 mr-2" />
                    NLM 비디오
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleNotebookLm('infographic')}>
                    <FileText className="h-3.5 w-3.5 mr-2" />
                    NLM 인포그래픽
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleNotebookLm('slide_deck')}>
                    <Layers className="h-3.5 w-3.5 mr-2" />
                    NLM 슬라이드
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleNotebookLm('mindmap')}>
                    <Brain className="h-3.5 w-3.5 mr-2" />
                    NLM 마인드맵
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleNotebookLm('quiz')}>
                    <ListChecks className="h-3.5 w-3.5 mr-2" />
                    NLM 퀴즈
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleNotebookLm('flashcards')}>
                    <FileText className="h-3.5 w-3.5 mr-2" />
                    NLM 플래시카드
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleNotebookLm('briefing')}>
                    <FileText className="h-3.5 w-3.5 mr-2" />
                    NLM 브리핑
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleNotebookLm('study_guide')}>
                    <FileText className="h-3.5 w-3.5 mr-2" />
                    NLM 스터디 가이드
                  </DropdownMenuItem>
                </>
              )}
              {(report.url || report.transcript) && (
                <DropdownMenuItem onClick={handleExtractEvents} disabled={eventLoading}>
                  <ListChecks className="h-3.5 w-3.5 mr-2" />
                  {eventLoading ? '추출 중...' : '이벤트 추출'}
                </DropdownMenuItem>
              )}
              {report.url && (
                <DropdownMenuItem onClick={() => setPanel('chatOpen', true)}>
                  <Bot className="h-3.5 w-3.5 mr-2" />
                  영상에 질문하기
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleExportHtml}>
                <FileText className="h-3.5 w-3.5 mr-2" />
                {t('result.exportHtml')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExportFormat('markdown')}>
                <FileText className="h-3.5 w-3.5 mr-2" />
                마크다운 (.md)
              </DropdownMenuItem>
              {canExportAnki && (
                <DropdownMenuItem onClick={() => handleExportFormat('anki')}>
                  <Layers className="h-3.5 w-3.5 mr-2" />
                  Anki 덱 (.apkg)
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => removeReport(report.id)}
              >
                <Trash2 className="h-3.5 w-3.5 mr-2" />
                {t('result.delete')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </Card>
    </>
    </ReportProvider>
  );
});

// 감성 전체 표시용 설정
const SENTIMENT_CONFIG = {
  positive: { label: '긍정', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-500' },
  neutral:  { label: '중립', color: 'text-slate-500 dark:text-slate-400',   bg: 'bg-slate-400'   },
  negative: { label: '부정', color: 'text-rose-600 dark:text-rose-400',     bg: 'bg-rose-500'    },
} as const;

// 키워드 관련도에 따른 색상 (진할수록 관련도 높음)
function keywordOpacity(relevance: number): string {
  if (relevance >= 0.8) return 'opacity-100 font-semibold';
  if (relevance >= 0.6) return 'opacity-80';
  return 'opacity-60';
}

function NlpAnalysisSection({ analysis }: { analysis: NlpAnalysis }) {
  const [open, setOpen] = useState(false);
  const { sentiment, keywords } = analysis;
  const cfg = SENTIMENT_CONFIG[sentiment.overall];

  // 게이지 너비: score -1~1 → 0~100%
  const gaugeWidth = Math.round(((sentiment.score + 1) / 2) * 100);

  return (
    <div className="mt-5 border border-border/50 rounded-lg overflow-hidden">
      {/* 헤더 — 클릭하면 접기/펼치기 */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="NLP 분석 펼치기/접기"
        aria-expanded={open}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-muted/30 hover:bg-muted/50 transition-colors text-sm font-medium"
      >
        <span className="flex items-center gap-2">
          <span>NLP 분석</span>
          <span className={`text-xs font-normal ${cfg.color}`}>
            {cfg.label} ({sentiment.score >= 0 ? '+' : ''}{sentiment.score.toFixed(2)})
          </span>
        </span>
        {open ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />}
      </button>

      {/* 항상 보이는 요약: 키워드 태그 + 감성 게이지 */}
      <div className="px-4 py-3 space-y-3">
        {/* 키워드 태그 */}
        {keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {keywords.slice(0, 8).map((kw) => (
              <span
                key={kw.word}
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-primary/10 text-primary ${keywordOpacity(kw.relevance)}`}
              >
                {kw.word}
              </span>
            ))}
          </div>
        )}

        {/* 감성 게이지 */}
        <div className="space-y-1">
          <div className="flex justify-between text-[11px] text-muted-foreground">
            <span>부정</span>
            <span>중립</span>
            <span>긍정</span>
          </div>
          <div className="relative h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className={`absolute left-0 top-0 h-full rounded-full ${cfg.bg} transition-all`}
              style={{ width: `${gaugeWidth}%` }}
            />
            {/* 중립선 */}
            <div className="absolute left-1/2 top-0 h-full w-px bg-border/60" />
          </div>
        </div>
      </div>

      {/* 상세 대시보드 (펼쳐질 때만) */}
      {open && <AnalysisDashboard analysis={analysis} />}
    </div>
  );
}

export default ResultCard;
