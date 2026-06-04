'use client';

import { memo, useEffect, useState, useMemo, useCallback, useReducer, useRef } from 'react';
import {
  Copy, Check, ChevronDown, ChevronUp, MoreHorizontal, Trash2,
  FileText, Code, Brain, Download, Share2, Printer,
  Zap, Type, MessageSquare, ExternalLink, Layers, Mic, Calendar, Bot, ListChecks, RefreshCw, AlertTriangle,
} from 'lucide-react';
import dynamic from 'next/dynamic';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import DOMPurify from 'dompurify';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
// KaTeX는 수식 감지 시에만 동적 로드 (초기 번들 ~280KB 절감)
// remark-math + rehype-katex는 MathMarkdown 컴포넌트에서 조건부 import
import { toast } from 'sonner';
import type { Report, QualityScore, NlpAnalysis, ViewMode, NotebookLmArtifact } from '@/lib/types';
import { getStyleLabel } from '@/lib/helpers';
import { useResultStore } from '@/stores/resultStore';
import { useUIStore } from '@/stores/uiStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { useTranslation } from '@/hooks/useTranslation';
import { exportDocx, exportFormat, exportHtml, extractEvents, notebookLmGenerate, notebookLmStatus, notebookLmAuthCheck } from '@/lib/api';
import { NotebookLmSection } from './NotebookLmSection';
import ContextMenu from './ContextMenu';
import type { VideoEvent, EventSummary } from '@/lib/types';

import { ReportProvider } from './ReportContext';

// 조건부 서브컴포넌트 — 특정 스타일/데이터에서만 사용되므로 dynamic import
const AudioPlayer = dynamic(() => import('./AudioPlayer'), { ssr: false });
const SeoSection = dynamic(() => import('./SeoSection'), { ssr: false });
const GeoSection = dynamic(() => import('./GeoSection'), { ssr: false });
const FaqCtaSection = dynamic(() => import('./FaqCtaSection'), { ssr: false });
const FusionSections = dynamic(() => import('./FusionSections'), { ssr: false });
const ShortsClipList = dynamic(() => import('./ShortsClipList'), { ssr: false });
const WebSourcesSection = dynamic(() => import('./WebSourcesSection'), { ssr: false });
const InsertedLinksSection = dynamic(() => import('./InsertedLinksSection'), { ssr: false });
const EventTimeline = dynamic(() => import('./EventTimeline'), { ssr: false });
const QaGateBadge = dynamic(() => import('./QaGateBadge'), { ssr: false });

// 무거운 서브컴포넌트 dynamic import
const VideoChatPanel = dynamic(() => import('@/components/chat/VideoChatPanel'), { ssr: false });
const PlatformRewriteModal = dynamic(() => import('./PlatformRewriteModal'), { ssr: false });
const AnalysisDashboard = dynamic(() => import('./AnalysisDashboard'), { ssr: false });
const TranscriptPanel = dynamic(() => import('./TranscriptPanel'), { ssr: false });
const ChapterTimeline = dynamic(() => import('./ChapterTimeline'), { ssr: false });

// KaTeX 수식 렌더링 — 콘텐츠에 수식 패턴이 있을 때만 로드
const MathMarkdown = dynamic(() => import('./MathMarkdown'), { ssr: false });

/** DOMPurify 기반 HTML 새니타이징 (XSS 방지) */
function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['h1','h2','h3','h4','h5','h6','p','br','strong','em','b','i','u','s',
      'ul','ol','li','a','img','table','thead','tbody','tr','th','td',
      'blockquote','pre','code','span','div','hr','sup','sub','mark'],
    ALLOWED_ATTR: ['href','src','alt','class','style','target','rel','colspan','rowspan'],
    ALLOW_DATA_ATTR: false,
  });
}

interface ResultCardProps {
  report: Report;
  searchQuery?: string;
  onSchedule: (report: Report) => void;
  viewMode?: ViewMode;
  /** compact 모드에서 카드 클릭 시 full 전환 콜백 */
  onExpandToFull?: () => void;
}

const remarkPlugins = [remarkGfm];
// 수식 감지 패턴: $$...$$ 또는 \(...\) 또는 \[...\]
const MATH_PATTERN = /\$\$[\s\S]+?\$\$|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\]/;

// 품질 등급별 스타일 정의
const GRADE_STYLES: Record<QualityScore['grade'], { badge: string; label: string }> = {
  A: { badge: 'border-green-500/50 text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400', label: 'A등급' },
  B: { badge: 'border-blue-500/50 text-blue-600 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-400', label: 'B등급' },
  C: { badge: 'border-yellow-500/50 text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400', label: 'C등급' },
  D: { badge: 'border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400', label: 'D등급' },
};

// 패널 상태 리듀서 — 13개 useState → 단일 리듀서 (상태 변경 시 1회 리렌더)
interface PanelState {
  collapsed: boolean;
  hasExpanded: boolean;
  copiedField: string | null;
  readPreviewMode: 'rendered' | 'markdown' | 'html' | 'timeline';
  notebookLmAuthNotice: string | null;
  exportNotice: string | null;
  focusedFromPanel: boolean;
  chatOpen: boolean;
  showTranscript: boolean;
  audioBlob: Blob | null;
  ttsLoading: boolean;
  eventOpen: boolean;
  eventLoading: boolean;
  extractedEvents: VideoEvent[] | null;
  eventSummary: EventSummary | null;
  rewriteOpen: boolean;
}
type PanelAction =
  | { type: 'SET'; key: keyof PanelState; value: PanelState[keyof PanelState] }
  | { type: 'BATCH'; updates: Partial<PanelState> };

const panelInitial: PanelState = {
  collapsed: false, hasExpanded: true, copiedField: null,
  readPreviewMode: 'rendered',
  notebookLmAuthNotice: null,
  exportNotice: null,
  focusedFromPanel: false,
  chatOpen: false, showTranscript: false, audioBlob: null, ttsLoading: false,
  eventOpen: false, eventLoading: false, extractedEvents: null, eventSummary: null,
  rewriteOpen: false,
};

function panelReducer(state: PanelState, action: PanelAction): PanelState {
  if (action.type === 'SET') {
    if (state[action.key] === action.value) return state;
    return { ...state, [action.key]: action.value };
  }
  // BATCH: 여러 상태를 한 번에 업데이트 (리렌더 1회)
  return { ...state, ...action.updates };
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const ResultCard = memo(function ResultCard({ report, searchQuery, onSchedule, viewMode = 'full', onExpandToFull }: ResultCardProps) {
  const [panel, dispatch] = useReducer(panelReducer, panelInitial);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { collapsed, hasExpanded, copiedField, readPreviewMode, notebookLmAuthNotice, exportNotice, focusedFromPanel, chatOpen, showTranscript, audioBlob, ttsLoading, eventOpen, eventLoading, extractedEvents, eventSummary, rewriteOpen } = panel;

  // 간편 setter
  const setPanel = useCallback(<K extends keyof PanelState>(key: K, value: PanelState[K]) => {
    dispatch({ type: 'SET', key, value });
  }, []);

  useEffect(() => {
    const openRewrite = (event: Event) => {
      const detail = (event as CustomEvent<{ reportId?: string }>).detail;
      if (detail?.reportId && detail.reportId !== report.id) return;
      onExpandToFull?.();
      setPanel('rewriteOpen', true);
    };

    window.addEventListener('insight-engine-open-rewrite', openRewrite);
    return () => window.removeEventListener('insight-engine-open-rewrite', openRewrite);
  }, [onExpandToFull, report.id, setPanel]);

  useEffect(() => {
    const focusReport = (event: Event) => {
      const detail = (event as CustomEvent<{ reportId?: string }>).detail;
      if (detail?.reportId !== report.id) return;
      onExpandToFull?.();
      setPanel('focusedFromPanel', true);
      window.setTimeout(() => setPanel('focusedFromPanel', false), 2500);
    };

    window.addEventListener('insight-engine-focus-report', focusReport);
    return () => window.removeEventListener('insight-engine-focus-report', focusReport);
  }, [onExpandToFull, report.id, setPanel]);

  // Zustand selector — 함수 참조만 구독 (전체 스토어 구독 방지)
  const removeReport = useResultStore((s) => s.removeReport);
  const updateReport = useResultStore((s) => s.updateReport);
  const setPromptModalOpen = useUIStore((s) => s.setPromptModalOpen);

  const selectedModel = useSettingsStore((s) => s.selectedModel);
  const { t } = useTranslation();

  const contentSelectionRef = useRef<HTMLDivElement>(null);
  const contentRegionId = `result-content-${report.id.replace(/[^A-Za-z0-9_-]/g, '-')}`;
  const charCount = report.content.length;

  const requestDelete = useCallback(() => {
    setDeleteConfirmOpen(true);
  }, []);

  const confirmDelete = useCallback(() => {
    removeReport(report.id);
    setDeleteConfirmOpen(false);
    toast.success('결과를 삭제했습니다.');
  }, [removeReport, report.id]);

  async function copyText(text: string, field: string) {
    await navigator.clipboard.writeText(text);
    setPanel('copiedField', field);
    toast.success(t('result.copied'));
    setTimeout(() => setPanel('copiedField', null), 2000);
  }

  async function copyRich() {
    try {
      const html = report.html || report.content;
      const blob = new Blob([html], { type: 'text/html' });
      const textBlob = new Blob([report.content], { type: 'text/plain' });
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': blob,
          'text/plain': textBlob,
        }),
      ]);
      setPanel('copiedField', 'rich');
      toast.success(t('result.richCopied'));
      setTimeout(() => setPanel('copiedField', null), 2000);
    } catch {
      await copyText(report.content, 'content');
    }
  }

  async function handleExportDocx() {
    try {
      const blob = await exportDocx(report.title, report.content);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.slice(0, 50)}.docx`;
      a.click();
      URL.revokeObjectURL(url);
      setPanel('exportNotice', 'DOCX 내보내기 완료');
      toast.success(t('result.docxSuccess'));
    } catch {
      setPanel('exportNotice', 'DOCX 내보내기 실패');
      toast.error(t('result.docxError'));
    }
  }

  async function handleExportHtml() {
    try {
      const blob = await exportHtml(report.title, report.content, report.html);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.slice(0, 50)}.html`;
      a.click();
      URL.revokeObjectURL(url);
      setPanel('exportNotice', 'HTML 내보내기 완료');
      toast.success(t('result.htmlSuccess'));
    } catch {
      setPanel('exportNotice', 'HTML 내보내기 실패');
      toast.error('HTML 내보내기 실패');
    }
  }

  function handlePrint() {
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`<!DOCTYPE html>
<html><head><title>${report.title}</title>
<style>body{font-family:sans-serif;max-width:800px;margin:2rem auto;line-height:1.6;color:#111}
@media print{body{margin:0}}</style></head>
<body>${sanitizeHtml(report.html || report.content)}</body></html>`);
    w.document.close();
    w.print();
  }

  function handleShare() {
    const text = `${report.title}\n\n${report.content.slice(0, 200)}...\n\n${report.url}`;
    navigator.clipboard.writeText(text);
    toast.success(t('result.shareCopied'));
  }

  async function handleExportFormat(format: 'markdown' | 'txt' | 'zip') {
    try {
      const blob = await exportFormat(format, report.title, report.content);
      const ext = format === 'markdown' ? 'md' : format;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.slice(0, 50)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
      setPanel('exportNotice', `${ext.toUpperCase()} 내보내기 완료`);
      toast.success(`${ext.toUpperCase()} 내보내기 완료`);
    } catch {
      setPanel('exportNotice', `${format.toUpperCase()} 내보내기 실패`);
      toast.error('내보내기에 실패했습니다.');
    }
  }

  async function handleNotebookLm(contentType: string) {
    dispatch({ type: 'BATCH', updates: { hasExpanded: true, collapsed: false, notebookLmAuthNotice: null } });

    const currentArtifacts = () => (
      useResultStore
        .getState()
        .reports
        .find((r) => r.id === report.id)
        ?.notebooklm
        ?.artifacts ?? []
    );
    const writeArtifacts = (artifacts: NotebookLmArtifact[]) => {
      updateReport(report.id, { notebooklm: { artifacts } });
    };

    const sourceText = report.transcript || report.content;
    const sourceUrl = report.url || `direct:${report.id}`;
    const tempId = `pending-${contentType}-${Date.now()}`;
    const pendingArtifact: NotebookLmArtifact = {
      artifact_id: tempId,
      content_type: contentType,
      status: 'in_progress',
    };
    writeArtifacts([...currentArtifacts(), pendingArtifact]);

    const removePendingArtifact = () => {
      writeArtifacts(currentArtifacts().filter((a) => a.artifact_id !== tempId));
    };

    const auth = await notebookLmAuthCheck().catch(() => null);
    if (!auth?.valid) {
      removePendingArtifact();
      const message = auth?.message || 'NotebookLM 인증이 필요합니다. 터미널에서 nlm login을 실행해주세요.';
      setPanel('notebookLmAuthNotice', message);
      toast.error(message);
      return;
    }

    try {
      const res = await notebookLmGenerate({
        type: contentType,
        url: sourceUrl,
        source_text: sourceText,
      });
      const artifact: NotebookLmArtifact = {
        artifact_id: res.artifact_id,
        content_type: contentType,
        status: 'in_progress',
      };
      writeArtifacts(currentArtifacts().map((a) => (a.artifact_id === tempId ? artifact : a)));
      toast.success(`NotebookLM ${contentType} 생성 시작`);

      const poll = setInterval(async () => {
        try {
          const status = await notebookLmStatus(res.artifact_id);
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(poll);
            writeArtifacts(currentArtifacts().map((a) => (
              a.artifact_id === res.artifact_id
                ? { ...a, status: status.status as 'completed' | 'failed' }
                : a
            )));
            if (status.status === 'completed') toast.success(`NotebookLM ${contentType} 생성 완료!`);
            else toast.error(`NotebookLM ${contentType} 생성 실패`);
          }
        } catch {
          clearInterval(poll);
        }
      }, 5000);
    } catch (err) {
      removePendingArtifact();
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

  /**
   * 마크다운 콘텐츠에서 [HH:MM:SS] 형식의 타임코드를 YouTube 딥링크로 변환합니다.
   * 영상 URL이 없거나 타임코드가 없으면 원본 텍스트를 그대로 반환합니다.
   */
  function injectTimestampLinks(content: string, videoUrl: string | undefined): string {
    if (!videoUrl) return content;
    return content.replace(/\[(\d{1,2}:\d{2}:\d{2})\]/g, (_, hhmmss) => {
      const parts = hhmmss.split(':').map(Number);
      const seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
      const separator = videoUrl.includes('?') ? '&' : '?';
      const deeplink = `${videoUrl}${separator}t=${seconds}`;
      return `[[${hhmmss}]](${deeplink})`;
    });
  }

  // html이 비어있고 content가 있으면 스트리밍 진행 중
  const isStreaming = !report.html && report.content.length > 0;

  // ReactMarkdown은 비싸므로 스트리밍 완료 후에만 렌더링
  const processedContent = useMemo(
    () => isStreaming ? report.content : injectTimestampLinks(report.content, report.url),
    [isStreaming, report.content, report.url],
  );

  const hasMath = useMemo(() => MATH_PATTERN.test(processedContent), [processedContent]);

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
  const videoId = report.url?.match(/(?:v=|youtu\.be\/)([^&]+)/)?.[1];

  const readPreviewBody = useMemo(() => {
    if (readPreviewMode === 'markdown') {
      return (
        <pre
          data-testid="result-markdown-preview"
          className="max-h-[560px] overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-200 bg-slate-950 p-4 text-sm leading-6 text-slate-50"
        >
          {processedContent}
        </pre>
      );
    }

    if (readPreviewMode === 'html') {
      return (
        <div
          data-testid="result-html-preview"
          className="prose max-w-none rounded-2xl border border-slate-200 bg-white p-4 text-[15.5px] leading-relaxed"
          dangerouslySetInnerHTML={{ __html: sanitizeHtml(report.html || report.content) }}
        />
      );
    }

    const wantsTimeline = readPreviewMode === 'timeline' || viewMode === 'timeline';
    if (wantsTimeline && report.chapters && report.chapters.length > 0) {
      return (
        <>
          <ChapterTimeline chapters={report.chapters} videoUrl={report.url} />
          <div className="mt-5 space-y-4">
            {report.chapters.map((ch, i) => (
              <div key={i} className="border-l-2 border-primary/30 pl-4">
                <h4 className="text-sm font-semibold mb-1">{ch.title}</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">{ch.summary}</p>
              </div>
            ))}
          </div>
          <details className="mt-5">
            <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
              전체 콘텐츠 보기
            </summary>
            <div className="prose max-w-none text-[15.5px] leading-relaxed mt-3">
              {markdownBody}
            </div>
          </details>
        </>
      );
    }

    if (wantsTimeline && report.transcript_segments && report.transcript_segments.length > 0) {
      return (
        <TranscriptPanel
          segments={report.transcript_segments}
          videoId={videoId}
        />
      );
    }

    if (wantsTimeline) {
      return (
        <>
          <div className="text-xs text-muted-foreground mb-3 px-3 py-2 bg-muted/30 rounded-md">
            이 콘텐츠에는 챕터나 자막 타임라인 데이터가 없어 전체 보기로 표시합니다.
          </div>
          <div data-testid="result-rendered-preview" className="prose max-w-none text-[15.5px] leading-relaxed">
            {markdownBody}
          </div>
        </>
      );
    }

    if (showTranscript && report.transcript_segments && report.transcript_segments.length > 0) {
      return (
        <TranscriptPanel
          segments={report.transcript_segments}
          videoId={videoId}
        />
      );
    }

    return (
      <div data-testid="result-rendered-preview" className="prose max-w-none text-[15.5px] leading-relaxed">
        {markdownBody}
      </div>
    );
  }, [
    markdownBody,
    processedContent,
    readPreviewMode,
    report.chapters,
    report.content,
    report.html,
    report.transcript_segments,
    report.url,
    showTranscript,
    videoId,
    viewMode,
  ]);

  // --- Compact 모드: 요약 카드 ---
  if (viewMode === 'compact') {
    const preview = report.content.slice(0, 100) + (report.content.length > 100 ? '…' : '');
    return (
      <ReportProvider report={report}>
      <Card
        className="overflow-hidden rounded-[24px] border-slate-200/80 bg-white shadow-sm shadow-slate-200/60 hover:shadow-md transition-shadow cursor-pointer"
        onClick={onExpandToFull}
      >
        <div className="px-4 py-3">
          {/* 메타 칩 + 제목 */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs text-muted-foreground/70 font-medium">
              {getStyleLabel(report.style)}
            </span>
            <span className="text-xs text-muted-foreground">{report.time}</span>
            <span className="ml-auto text-[11px] text-muted-foreground inline-flex items-center gap-1">
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

  const workbenchButtonClass = 'h-9 justify-start gap-2 rounded-xl bg-white/80 px-3 text-xs';
  const workbenchSectionClass = 'rounded-2xl border border-slate-200/80 bg-white/65 p-3 shadow-sm';

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
    <PlatformRewriteModal
      open={rewriteOpen}
      onOpenChange={(open) => setPanel('rewriteOpen', open)}
      content={report.content}
    />
    <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            결과 삭제
          </DialogTitle>
          <DialogDescription>
            “{report.title}” 결과를 삭제합니다. 이 작업은 되돌릴 수 없습니다.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
            취소
          </Button>
          <Button type="button" variant="destructive" onClick={confirmDelete}>
            삭제하기
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    <Card className={`overflow-hidden rounded-[24px] border-slate-200/80 bg-white shadow-sm shadow-slate-200/60 transition-all duration-200 hover:border-slate-300 hover:shadow-md ${focusedFromPanel ? 'ring-2 ring-indigo-400 shadow-indigo-100' : ''}`}>
      {/* 헤더 */}
      <div className="px-6 pt-6 pb-3">
        {/* 뱃지 + 액션 */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground/70 font-medium">
              {getStyleLabel(report.style)}
            </span>
            <span className="text-xs text-muted-foreground">{report.time}</span>
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
            <QaGateBadge content={report.content} />
          </div>
          <div className="flex items-center gap-1">
            {report.transcript_segments && report.transcript_segments.length > 0 && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    data-testid="result-action-transcript-toggle"
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    aria-label={showTranscript ? '요약 보기' : '자막 보기'}
                    aria-pressed={showTranscript}
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
                  data-testid="result-action-rich-copy"
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  aria-label={copiedField === 'rich' ? '서식 유지 복사 완료' : '서식 유지 복사'}
                  aria-describedby="result-action-rich-copy-help"
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
            <span id="result-action-rich-copy-help" data-testid="result-action-rich-copy-help" className="sr-only">
              HTML과 텍스트 형식을 함께 클립보드에 복사합니다.
            </span>
            <Button
              data-testid="result-action-collapse-toggle"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              aria-label={collapsed ? '카드 펼치기' : '카드 접기'}
              aria-expanded={!collapsed}
              aria-controls={contentRegionId}
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
        <h3 className="font-semibold text-xl leading-snug tracking-tight">{report.title}</h3>

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
      <>
      <CardContent
        id={contentRegionId}
        ref={contentSelectionRef}
        data-testid="result-content-selection-area"
        role="region"
        aria-label={`${report.title} 본문`}
        className="px-6 pb-5 pt-4 border-t border-border/50"
        style={{ display: collapsed ? 'none' : undefined }}
      >
          {readPreviewBody}

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

          {/* FAQ + CTA 섹션 (blog_seo, geo_seo 스타일) */}
          {(report.faq_schema || report.cta) && (
            <FaqCtaSection faqSchema={report.faq_schema} cta={report.cta} />
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

          {/* 팟캐스트 오디오 플레이어 */}
          {audioBlob && (
            <AudioPlayer
              audioBlob={audioBlob}
              title={report.title}
              onClose={() => setPanel('audioBlob', null)}
            />
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
        <ContextMenu containerRef={contentSelectionRef} />
      </>
      )}

      {/* 푸터 */}
      {/* Studio Workbench */}
      <div
        className="border-t border-slate-200/70 bg-gradient-to-r from-slate-50 via-white to-indigo-50/40 px-6 py-4"
        data-testid="result-workbench"
        role="region"
        aria-labelledby="result-workbench-title"
      >
        <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p id="result-workbench-title" className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600">Result Workbench</p>
            <p className="text-sm text-slate-500">메뉴 없이 복사, 변환, NLM 산출물, 내보내기, 예약까지 바로 처리합니다.</p>
          </div>
          <span className="text-xs text-slate-400">{(report.notebooklm?.artifacts?.length ?? 0)} NLM · {charCount.toLocaleString()}자</span>
        </div>
        <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
          <section data-testid="workbench-section-read" role="region" aria-labelledby="workbench-section-read-title" className={workbenchSectionClass}>
            <p id="workbench-section-read-title" className="mb-2 text-xs font-semibold text-slate-500">읽기</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Button data-testid="workbench-action-copy-title" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => copyText(report.title, 'title')}>
                <Copy className="h-3.5 w-3.5 text-indigo-600" />제목 복사
              </Button>
              <Button data-testid="workbench-action-copy-content" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => copyText(report.content, 'content')}>
                <FileText className="h-3.5 w-3.5 text-indigo-600" />본문 복사
              </Button>
              <Button data-testid="workbench-action-copy-rich" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={copyRich} aria-label="리치 복사" aria-describedby="workbench-copy-rich-help">
                <Type className="h-3.5 w-3.5 text-indigo-600" />리치 복사
              </Button>
              <span id="workbench-copy-rich-help" data-testid="workbench-copy-rich-help" className="sr-only">
                HTML과 텍스트 형식을 함께 클립보드에 복사합니다.
              </span>
              <Button
                data-testid="workbench-action-toggle-transcript"
                type="button"
                variant="outline"
                size="sm"
                className={workbenchButtonClass}
                onClick={() => setPanel('showTranscript', !showTranscript)}
                disabled={!report.transcript_segments || report.transcript_segments.length === 0}
                aria-label={showTranscript ? '요약 보기' : '자막 보기'}
                aria-pressed={showTranscript}
              >
                <FileText className="h-3.5 w-3.5 text-indigo-600" />{showTranscript ? '요약 보기' : '자막 보기'}
              </Button>
            </div>
            <div className="mt-3 border-t border-slate-200/70 pt-3">
              <p className="mb-2 text-[11px] font-semibold text-slate-400">미리보기 전환</p>
              <div data-testid="workbench-preview-actions" role="toolbar" aria-label="미리보기 전환" className="grid gap-2 sm:grid-cols-2">
                <Button
                  data-testid="workbench-action-preview-rendered"
                  type="button"
                  variant={readPreviewMode === 'rendered' ? 'default' : 'outline'}
                  size="sm"
                  className={workbenchButtonClass}
                  onClick={() => setPanel('readPreviewMode', 'rendered')}
                  aria-pressed={readPreviewMode === 'rendered'}
                  aria-controls={contentRegionId}
                >
                  <FileText className="h-3.5 w-3.5" />본문 보기
                </Button>
                <Button
                  data-testid="workbench-action-preview-markdown"
                  type="button"
                  variant={readPreviewMode === 'markdown' ? 'default' : 'outline'}
                  size="sm"
                  className={workbenchButtonClass}
                  onClick={() => setPanel('readPreviewMode', 'markdown')}
                  aria-pressed={readPreviewMode === 'markdown'}
                  aria-controls={contentRegionId}
                >
                  <Code className="h-3.5 w-3.5" />Markdown
                </Button>
                <Button
                  data-testid="workbench-action-preview-html"
                  type="button"
                  variant={readPreviewMode === 'html' ? 'default' : 'outline'}
                  size="sm"
                  className={workbenchButtonClass}
                  onClick={() => setPanel('readPreviewMode', 'html')}
                  aria-pressed={readPreviewMode === 'html'}
                  aria-controls={contentRegionId}
                >
                  <Type className="h-3.5 w-3.5" />HTML
                </Button>
                <Button
                  data-testid="workbench-action-timeline"
                  type="button"
                  variant={readPreviewMode === 'timeline' ? 'default' : 'outline'}
                  size="sm"
                  className={workbenchButtonClass}
                  onClick={() => setPanel('readPreviewMode', 'timeline')}
                  aria-pressed={readPreviewMode === 'timeline'}
                  aria-controls={contentRegionId}
                >
                  <ListChecks className="h-3.5 w-3.5" />타임라인
                </Button>
              </div>
            </div>
          </section>

          <section data-testid="workbench-section-improve" role="region" aria-labelledby="workbench-section-improve-title" className={workbenchSectionClass}>
            <p id="workbench-section-improve-title" className="mb-2 text-xs font-semibold text-slate-500">개선</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Button data-testid="workbench-action-prompt" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => setPromptModalOpen(true, report.prompt)}>
                <Code className="h-3.5 w-3.5 text-indigo-600" />프롬프트
              </Button>
              <Button data-testid="workbench-action-rewrite" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => setPanel('rewriteOpen', true)}>
                <RefreshCw className="h-3.5 w-3.5 text-indigo-600" />플랫폼 변환
              </Button>
              <Button data-testid="workbench-action-events" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={handleExtractEvents} disabled={eventLoading || !(report.url || report.transcript)}>
                <ListChecks className="h-3.5 w-3.5 text-indigo-600" />{eventLoading ? '추출 중...' : '이벤트'}
              </Button>
              <Button data-testid="workbench-action-video-qa" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => setPanel('chatOpen', true)} disabled={!report.url}>
                <Bot className="h-3.5 w-3.5 text-indigo-600" />영상 Q&A
              </Button>
            </div>
          </section>

          <section data-testid="workbench-section-nlm" role="region" aria-labelledby="workbench-section-nlm-title" className={workbenchSectionClass}>
            <p id="workbench-section-nlm-title" className="mb-2 text-xs font-semibold text-slate-500">NLM 산출물</p>
            {notebookLmAuthNotice && (
              <div
                data-testid="workbench-nlm-auth-notice"
                role="status"
                aria-live="polite"
                className="mb-3 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800"
              >
                <div className="flex items-start gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    <p className="font-semibold">NotebookLM 인증이 필요합니다</p>
                    <p className="mt-1">{notebookLmAuthNotice}</p>
                  </div>
                </div>
              </div>
            )}
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              <Button data-testid="workbench-action-nlm-video" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleNotebookLm('video')}>
                <Layers className="h-3.5 w-3.5 text-indigo-600" />비디오
              </Button>
              <Button data-testid="workbench-action-nlm-infographic" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleNotebookLm('infographic')}>
                <FileText className="h-3.5 w-3.5 text-indigo-600" />인포그래픽
              </Button>
              <Button data-testid="workbench-action-nlm-slide-deck" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleNotebookLm('slide_deck')}>
                <Layers className="h-3.5 w-3.5 text-indigo-600" />슬라이드
              </Button>
              <Button data-testid="workbench-action-nlm-mindmap" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleNotebookLm('mindmap')}>
                <Brain className="h-3.5 w-3.5 text-indigo-600" />마인드맵
              </Button>
              <Button data-testid="workbench-action-nlm-quiz" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleNotebookLm('quiz')}>
                <ListChecks className="h-3.5 w-3.5 text-indigo-600" />퀴즈
              </Button>
              <Button data-testid="workbench-action-nlm-flashcards" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleNotebookLm('flashcards')}>
                <FileText className="h-3.5 w-3.5 text-indigo-600" />플래시카드
              </Button>
              <Button data-testid="workbench-action-nlm-briefing" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleNotebookLm('briefing')}>
                <FileText className="h-3.5 w-3.5 text-indigo-600" />브리핑
              </Button>
              <Button data-testid="workbench-action-nlm-study-guide" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleNotebookLm('study_guide')}>
                <Brain className="h-3.5 w-3.5 text-indigo-600" />NLM 가이드
              </Button>
            </div>
          </section>

          <section data-testid="workbench-section-export" role="region" aria-labelledby="workbench-section-export-title" className={workbenchSectionClass}>
            <p id="workbench-section-export-title" className="mb-2 text-xs font-semibold text-slate-500">내보내기</p>
            {exportNotice && (
              <div
                data-testid="workbench-export-status"
                role="status"
                aria-live="polite"
                className="mb-3 rounded-2xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700"
              >
                {exportNotice}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <Button data-testid="workbench-action-export-html" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={handleExportHtml}>
                <FileText className="h-3.5 w-3.5 text-indigo-600" />HTML
              </Button>
              <Button data-testid="workbench-action-export-docx" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={handleExportDocx}>
                <Download className="h-3.5 w-3.5 text-indigo-600" />DOCX
              </Button>
              <Button data-testid="workbench-action-export-md" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleExportFormat('markdown')}>
                <FileText className="h-3.5 w-3.5 text-indigo-600" />MD
              </Button>
              <Button data-testid="workbench-action-export-txt" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleExportFormat('txt')}>
                <FileText className="h-3.5 w-3.5 text-indigo-600" />TXT
              </Button>
              <Button data-testid="workbench-action-export-zip" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => handleExportFormat('zip')}>
                <Download className="h-3.5 w-3.5 text-indigo-600" />ZIP
              </Button>
              <Button data-testid="workbench-action-print" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={handlePrint}>
                <Printer className="h-3.5 w-3.5 text-indigo-600" />PDF
              </Button>
            </div>
          </section>

          <section data-testid="workbench-section-publish" role="region" aria-labelledby="workbench-section-publish-title" className={workbenchSectionClass}>
            <p id="workbench-section-publish-title" className="mb-2 text-xs font-semibold text-slate-500">배포</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <Button data-testid="workbench-action-schedule" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={() => onSchedule(report)}>
                <Calendar className="h-3.5 w-3.5 text-indigo-600" />예약
              </Button>
              <Button data-testid="workbench-action-share" type="button" variant="outline" size="sm" className={workbenchButtonClass} onClick={handleShare}>
                <Share2 className="h-3.5 w-3.5 text-indigo-600" />공유
              </Button>
            </div>
          </section>

          <section data-testid="workbench-section-manage" role="region" aria-labelledby="workbench-section-manage-title" className={workbenchSectionClass}>
            <p id="workbench-section-manage-title" className="mb-2 text-xs font-semibold text-slate-500">관리</p>
            <Button data-testid="workbench-action-delete" type="button" variant="outline" size="sm" className={`${workbenchButtonClass} w-full text-red-600 hover:text-red-700`} onClick={requestDelete}>
              <Trash2 className="h-3.5 w-3.5" />삭제
            </Button>
          </section>
        </div>
      </div>

      <div className="px-6 py-3 border-t border-border/50 flex items-center justify-between text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Zap className="h-3 w-3" />
          {(report.usage?.total_tokens ?? 0).toLocaleString()} tokens · {(report.elapsed_time ?? 0).toFixed(1)}초 · {charCount.toLocaleString()}자
        </span>

        <div className="flex items-center gap-0.5">
          {/* 더보기 메뉴 */}
          <span className="mr-2 hidden text-xs font-medium text-slate-400 sm:inline">Workbench</span>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="더보기 메뉴" aria-haspopup="menu">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
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
              <DropdownMenuItem onClick={() => setPanel('rewriteOpen', true)}>
                <RefreshCw className="h-3.5 w-3.5 mr-2" />
                플랫폼 변환
              </DropdownMenuItem>
              <DropdownMenuSeparator />
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
              <DropdownMenuItem onClick={handleExportDocx}>
                <Download className="h-3.5 w-3.5 mr-2" />
                {t('result.exportDocx')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExportFormat('markdown')}>
                <FileText className="h-3.5 w-3.5 mr-2" />
                마크다운 (.md)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExportFormat('txt')}>
                <FileText className="h-3.5 w-3.5 mr-2" />
                텍스트 (.txt)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExportFormat('zip')}>
                <Download className="h-3.5 w-3.5 mr-2" />
                패키지 (.zip)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handlePrint}>
                <Printer className="h-3.5 w-3.5 mr-2" />
                {t('result.printPdf')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onSchedule(report)}>
                <Calendar className="h-3.5 w-3.5 mr-2" />
                {t('result.schedule')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleShare}>
                <Share2 className="h-3.5 w-3.5 mr-2" />
                {t('result.share')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={requestDelete}
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
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { sentiment, keywords, topics } = analysis;
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
