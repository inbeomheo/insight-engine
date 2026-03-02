'use client';

import { memo, useState, useMemo } from 'react';
import {
  Copy, Check, ChevronDown, ChevronUp, MoreHorizontal, Trash2,
  FileText, Code, Brain, Download, Share2, Printer,
  Zap, Type, MessageSquare, ExternalLink, Layers, Mic, Send, Calendar, Bot,
} from 'lucide-react';
import VideoChatPanel from '@/components/chat/VideoChatPanel';
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
import { toast } from 'sonner';
import type { Report, McpPlugin, QualityScore, NlpAnalysis } from '@/lib/types';
import { getStyleLabel } from '@/lib/helpers';
import { useResultStore } from '@/stores/resultStore';
import { useUIStore } from '@/stores/uiStore';
import { exportDocx, publishToMcp } from '@/lib/api';

import SeoSection from './SeoSection';
import GeoSection from './GeoSection';
import FaqCtaSection from './FaqCtaSection';
import FusionSections from './FusionSections';
import ShortsClipList from './ShortsClipList';
import AnalysisDashboard from './AnalysisDashboard';
import WebSourcesSection from './WebSourcesSection';

interface ResultCardProps {
  report: Report;
  searchQuery?: string;
  mcpPlugins: McpPlugin[];
  onSchedule: (report: Report) => void;
}

const remarkPlugins = [remarkGfm];

// 품질 등급별 스타일 정의
const GRADE_STYLES: Record<QualityScore['grade'], { badge: string; label: string }> = {
  A: { badge: 'border-green-500/50 text-green-600 bg-green-50 dark:bg-green-950/30 dark:text-green-400', label: 'A등급' },
  B: { badge: 'border-blue-500/50 text-blue-600 bg-blue-50 dark:bg-blue-950/30 dark:text-blue-400', label: 'B등급' },
  C: { badge: 'border-yellow-500/50 text-yellow-600 bg-yellow-50 dark:bg-yellow-950/30 dark:text-yellow-400', label: 'C등급' },
  D: { badge: 'border-red-500/50 text-red-600 bg-red-50 dark:bg-red-950/30 dark:text-red-400', label: 'D등급' },
};

const ResultCard = memo(function ResultCard({ report, searchQuery, mcpPlugins, onSchedule }: ResultCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  // Zustand selector — 함수 참조만 구독 (전체 스토어 구독 방지)
  const removeReport = useResultStore((s) => s.removeReport);
  const setPromptModalOpen = useUIStore((s) => s.setPromptModalOpen);
  const setMindmapModalOpen = useUIStore((s) => s.setMindmapModalOpen);

  const charCount = report.content.length;

  async function copyText(text: string, field: string) {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    toast.success('복사되었습니다');
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
      toast.success('서식 포함 복사 완료');
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
      toast.success('DOCX 다운로드 완료');
    } catch {
      toast.error('DOCX 내보내기 실패');
    }
  }

  function handleExportHtml() {
    const html = `<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><title>${report.title}</title>
<style>body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#111827}
h1,h2,h3{margin-top:1.5rem}a{color:#4F46E5}blockquote{border-left:3px solid #4F46E5;padding-left:1rem;color:#6B7280}
table{border-collapse:collapse;width:100%}th,td{border:1px solid #E5E7EB;padding:8px;text-align:left}
th{background:#F9FAFB}</style></head><body>${report.html || report.content}</body></html>`;
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.title.slice(0, 50)}.html`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('HTML 다운로드 완료');
  }

  function handlePrint() {
    const w = window.open('', '_blank');
    if (!w) return;
    w.document.write(`<!DOCTYPE html>
<html><head><title>${report.title}</title>
<style>body{font-family:sans-serif;max-width:800px;margin:2rem auto;line-height:1.6;color:#111}
@media print{body{margin:0}}</style></head>
<body>${report.html || report.content}</body></html>`);
    w.document.close();
    w.print();
  }

  function handleShare() {
    const text = `${report.title}\n\n${report.content.slice(0, 200)}...\n\n${report.url}`;
    navigator.clipboard.writeText(text);
    toast.success('공유 텍스트 복사 완료');
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
      toast.error('발행 중 오류가 발생했습니다.');
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

  // ReactMarkdown은 비싸므로 content가 바뀔 때만 재렌더
  const processedContent = useMemo(
    () => injectTimestampLinks(report.content, report.url),
    [report.content, report.url],
  );

  const markdownBody = useMemo(
    () => (
      <ReactMarkdown remarkPlugins={remarkPlugins}>
        {processedContent}
      </ReactMarkdown>
    ),
    [processedContent],
  );

  return (
    <>
    {chatOpen && report.url && (
      <VideoChatPanel
        videoUrl={report.url}
        videoTitle={report.youtube_title || report.title}
        onClose={() => setChatOpen(false)}
      />
    )}
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
          </div>
          <div className="flex items-center gap-1">
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
              <TooltipContent>서식 복사</TooltipContent>
            </Tooltip>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setCollapsed(!collapsed)}
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
                <span className="truncate">영상 {i + 1}: {sv.title}</span>
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
            {report.youtube_title || '원본 영상'}
          </a>
        ) : null}
      </div>

      {/* 본문 */}
      {!collapsed && (
        <CardContent className="px-6 pb-5 pt-4 border-t border-border/50">
          <div className="prose max-w-none text-[15.5px] leading-relaxed">
            {markdownBody}
          </div>

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
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem onClick={() => copyText(report.title, 'title')}>
                <Copy className="h-3.5 w-3.5 mr-2" />
                제목 복사
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => copyText(report.content, 'content')}>
                <FileText className="h-3.5 w-3.5 mr-2" />
                전체 복사
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setPromptModalOpen(true, report.prompt)}>
                <Code className="h-3.5 w-3.5 mr-2" />
                프롬프트 보기
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setMindmapModalOpen(true, report.id)}>
                <Brain className="h-3.5 w-3.5 mr-2" />
                마인드맵
              </DropdownMenuItem>
              {report.url && (
                <DropdownMenuItem onClick={() => setChatOpen(true)}>
                  <Bot className="h-3.5 w-3.5 mr-2" />
                  영상에 질문하기
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleExportHtml}>
                <FileText className="h-3.5 w-3.5 mr-2" />
                HTML 내보내기
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleExportDocx}>
                <Download className="h-3.5 w-3.5 mr-2" />
                DOCX 내보내기
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handlePrint}>
                <Printer className="h-3.5 w-3.5 mr-2" />
                PDF 인쇄
              </DropdownMenuItem>
              {mcpPlugins.length > 0 && (
                <>
                  <DropdownMenuSeparator />
                  {mcpPlugins.map((plugin) => (
                    <DropdownMenuItem key={plugin.id} onClick={() => handlePublish(plugin.id)}>
                      <Send className="h-3.5 w-3.5 mr-2" />
                      {plugin.name} 발행
                    </DropdownMenuItem>
                  ))}
                </>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onSchedule(report)}>
                <Calendar className="h-3.5 w-3.5 mr-2" />
                예약 발행
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleShare}>
                <Share2 className="h-3.5 w-3.5 mr-2" />
                공유
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => removeReport(report.id)}
              >
                <Trash2 className="h-3.5 w-3.5 mr-2" />
                삭제
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
