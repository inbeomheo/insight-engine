'use client';

import { memo, useState, useMemo, useCallback } from 'react';
import {
  Copy, Check, ChevronDown, ChevronUp, MoreHorizontal, Trash2,
  FileText, Code, Brain, Download, Share2, Printer,
  Zap, Type, MessageSquare, ExternalLink, Layers, Mic, Send, Calendar, Bot, Headphones, ListChecks, RefreshCw,
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
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { toast } from 'sonner';
import type { Report, McpPlugin, QualityScore, NlpAnalysis, ViewMode } from '@/lib/types';
import { getStyleLabel } from '@/lib/helpers';
import { useResultStore } from '@/stores/resultStore';
import { useUIStore } from '@/stores/uiStore';
import { useTranslation } from '@/hooks/useTranslation';
import { exportDocx, exportFormat, publishToMcp, synthesizeTts, extractEvents } from '@/lib/api';
import type { VideoEvent, EventSummary } from '@/lib/types';

import AudioPlayer from './AudioPlayer';
import SeoSection from './SeoSection';
import GeoSection from './GeoSection';
import FaqCtaSection from './FaqCtaSection';
import FusionSections from './FusionSections';
import ShortsClipList from './ShortsClipList';
import WebSourcesSection from './WebSourcesSection';
import InsertedLinksSection from './InsertedLinksSection';
import EventTimeline from './EventTimeline';
import QaGateBadge from './QaGateBadge';

// Phase 2: 무거운 서브컴포넌트 dynamic import (조건부 렌더링)
const VideoChatPanel = dynamic(() => import('@/components/chat/VideoChatPanel'), { ssr: false });
const PlatformRewriteModal = dynamic(() => import('./PlatformRewriteModal'), { ssr: false });
const AnalysisDashboard = dynamic(() => import('./AnalysisDashboard'), { ssr: false });
const TranscriptPanel = dynamic(() => import('./TranscriptPanel'), { ssr: false });
const ChapterTimeline = dynamic(() => import('./ChapterTimeline'), { ssr: false });

/** script 태그 및 이벤트 핸들러 속성 제거 */
function sanitizeHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<script[^>]*>/gi, '')
    .replace(/\s+on\w+\s*=\s*["'][^"']*["']/gi, '')
    .replace(/\s+on\w+\s*=\s*\S+/gi, '');
}

interface ResultCardProps {
  report: Report;
  searchQuery?: string;
  mcpPlugins: McpPlugin[];
  onSchedule: (report: Report) => void;
  viewMode?: ViewMode;
  /** compact 모드에서 카드 클릭 시 full 전환 콜백 */
  onExpandToFull?: () => void;
}

const remarkPlugins = [remarkGfm, remarkMath];
const rehypePlugins = [rehypeKatex];

// 품질 등급별 스타일 정의
const GRADE_STYLES: Record<QualityScore['grade'], { badge: string; label: string }> = {
  A: { badge: 'border-green-500/50 text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400', label: 'A등급' },
  B: { badge: 'border-blue-500/50 text-blue-600 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-400', label: 'B등급' },
  C: { badge: 'border-yellow-500/50 text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400', label: 'C등급' },
  D: { badge: 'border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400', label: 'D등급' },
};

const ResultCard = memo(function ResultCard({ report, searchQuery, mcpPlugins, onSchedule, viewMode = 'full', onExpandToFull }: ResultCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  // 한번이라도 펼쳤으면 DOM 유지 (display:none으로만 숨김 → 토글 즉시 반응)
  const [hasExpanded, setHasExpanded] = useState(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [ttsLoading, setTtsLoading] = useState(false);

  // 이벤트 추출 상태
  const [eventOpen, setEventOpen] = useState(false);
  const [eventLoading, setEventLoading] = useState(false);
  const [extractedEvents, setExtractedEvents] = useState<VideoEvent[] | null>(null);
  const [eventSummary, setEventSummary] = useState<EventSummary | null>(null);

  // 플랫폼 리라이트 모달
  const [rewriteOpen, setRewriteOpen] = useState(false);

  // Zustand selector — 함수 참조만 구독 (전체 스토어 구독 방지)
  const removeReport = useResultStore((s) => s.removeReport);
  const setPromptModalOpen = useUIStore((s) => s.setPromptModalOpen);
  const setMindmapModalOpen = useUIStore((s) => s.setMindmapModalOpen);
  const { t } = useTranslation();

  const charCount = report.content.length;

  async function copyText(text: string, field: string) {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    toast.success(t('result.copied'));
    setTimeout(() => setCopiedField(null), 2000);
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
      setCopiedField('rich');
      toast.success(t('result.richCopied'));
      setTimeout(() => setCopiedField(null), 2000);
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
      toast.success(t('result.docxSuccess'));
    } catch {
      toast.error(t('result.docxError'));
    }
  }

  function handleExportHtml() {
    const html = `<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>${report.title}</title>
<style>body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#111827}
h1,h2,h3{margin-top:1.5rem}a{color:#4F46E5}blockquote{border-left:3px solid #4F46E5;padding-left:1rem;color:#6B7280}
table{border-collapse:collapse;width:100%}th,td{border:1px solid #E5E7EB;padding:8px;text-align:left}
th{background:#F9FAFB}</style></head><body>${sanitizeHtml(report.html || report.content)}</body></html>`;
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title.slice(0, 50)}.html`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(t('result.htmlSuccess'));
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
      toast.success(`${ext.toUpperCase()} 내보내기 완료`);
    } catch {
      toast.error('내보내기에 실패했습니다.');
    }
  }

  async function handleTts() {
    if (ttsLoading) return;
    setTtsLoading(true);
    try {
      const blob = await synthesizeTts(report.content);
      setAudioBlob(blob);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '오디오 생성에 실패했습니다.');
    } finally {
      setTtsLoading(false);
    }
  }

  async function handlePublish(pluginId: string) {
    try {
      const res = await publishToMcp({
        plugin_id: pluginId,
        title: report.title,
        content: report.content,
      });
      if (res.success) {
        toast.success(res.message);
      } else {
        toast.error(res.message);
      }
    } catch {
      toast.error(t('result.publishError'));
    }
  }

  async function handleExtractEvents() {
    // 이미 추출된 경우 패널 토글만
    if (extractedEvents !== null) {
      setEventOpen((v) => !v);
      return;
    }

    setEventLoading(true);
    setEventOpen(true);

    try {
      const res = await extractEvents({
        url: report.url,
        transcript: report.transcript,
      });
      setExtractedEvents(res.events);
      setEventSummary(res.summary);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '이벤트 추출에 실패했습니다.');
      setEventOpen(false);
    } finally {
      setEventLoading(false);
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

  const markdownBody = useMemo(
    () => isStreaming ? (
      <div className="whitespace-pre-wrap">{processedContent}</div>
    ) : (
      <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins}>
        {processedContent}
      </ReactMarkdown>
    ),
    [isStreaming, processedContent],
  );

  // --- Compact 모드: 요약 카드 ---
  if (viewMode === 'compact') {
    const preview = report.content.slice(0, 100) + (report.content.length > 100 ? '…' : '');
    return (
      <Card
        className="overflow-hidden border-border/40 shadow-none hover:shadow-sm transition-shadow cursor-pointer"
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
    );
  }

  return (
    <>
    {chatOpen && report.url && (
      <VideoChatPanel
        videoUrl={report.url}
        videoTitle={report.youtube_title || report.title}
        onClose={() => setChatOpen(false)}
      />
    )}
    <PlatformRewriteModal
      open={rewriteOpen}
      onOpenChange={setRewriteOpen}
      content={report.content}
    />
    <Card className="overflow-hidden border-border/40 shadow-none hover:shadow-sm transition-shadow">
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
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => setShowTranscript((v) => !v)}
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
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
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
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              aria-label={collapsed ? '카드 펼치기' : '카드 접기'}
              onClick={() => {
                if (collapsed) setHasExpanded(true);
                setCollapsed(!collapsed);
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
      <CardContent className="px-6 pb-5 pt-4 border-t border-border/50" style={{ display: collapsed ? 'none' : undefined }}>
          {/* 타임라인 모드: 챕터 우선 표시 + 챕터별 콘텐츠 */}
          {viewMode === 'timeline' && report.chapters && report.chapters.length > 0 ? (
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
              {/* 타임라인 모드에서도 전체 콘텐츠 접기 가능하도록 표시 */}
              <details className="mt-5">
                <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors">
                  전체 콘텐츠 보기
                </summary>
                <div className="prose max-w-none text-[15.5px] leading-relaxed mt-3">
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
                <div className="prose max-w-none text-[15.5px] leading-relaxed">
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
                <div className="prose max-w-none text-[15.5px] leading-relaxed">
                  {markdownBody}
                </div>
              )}

              {/* 챕터 타임라인 (full 모드에서만 기존 위치에 표시) */}
              {report.chapters && report.chapters.length > 0 && (
                <ChapterTimeline chapters={report.chapters} videoUrl={report.url} />
              )}
            </>
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
              onClose={() => setAudioBlob(null)}
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
                  onClick={() => setEventOpen(false)}
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
      <div className="px-6 py-3 border-t border-border/50 flex items-center justify-between text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Zap className="h-3 w-3" />
          {(report.usage?.total_tokens ?? 0).toLocaleString()} tokens · {(report.elapsed_time ?? 0).toFixed(1)}초 · {charCount.toLocaleString()}자
        </span>

        <div className="flex items-center gap-0.5">
          {/* 더보기 메뉴 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="더보기 메뉴">
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
              <DropdownMenuItem onClick={() => setMindmapModalOpen(true, report.id)}>
                <Brain className="h-3.5 w-3.5 mr-2" />
                {t('result.mindmap')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setRewriteOpen(true)}>
                <RefreshCw className="h-3.5 w-3.5 mr-2" />
                플랫폼 변환
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleTts} disabled={ttsLoading}>
                <Headphones className="h-3.5 w-3.5 mr-2" />
                {ttsLoading ? '변환 중...' : '팟캐스트로 변환'}
              </DropdownMenuItem>
              {(report.url || report.transcript) && (
                <DropdownMenuItem onClick={handleExtractEvents} disabled={eventLoading}>
                  <ListChecks className="h-3.5 w-3.5 mr-2" />
                  {eventLoading ? '추출 중...' : '이벤트 추출'}
                </DropdownMenuItem>
              )}
              {report.url && (
                <DropdownMenuItem onClick={() => setChatOpen(true)}>
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
              {mcpPlugins.length > 0 && (
                <>
                  <DropdownMenuSeparator />
                  {mcpPlugins.map((plugin) => (
                    <DropdownMenuItem key={plugin.id} onClick={() => handlePublish(plugin.id)}>
                      <Send className="h-3.5 w-3.5 mr-2" />
                      {t('result.publish', { name: plugin.name })}
                    </DropdownMenuItem>
                  ))}
                </>
              )}
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
