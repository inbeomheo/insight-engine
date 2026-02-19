'use client';

import { useState, useMemo } from 'react';
import {
  Copy, Check, ChevronDown, ChevronUp, MoreHorizontal, Trash2,
  FileText, Code, Brain, Download, Share2, RefreshCw, Printer,
  Clock, Zap, Type, Hash, MessageSquare, ExternalLink, Layers,
} from 'lucide-react';
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
import type { Report } from '@/lib/types';
import { STYLE_OPTIONS } from '@/lib/constants';
import { useResultStore } from '@/stores/resultStore';
import { useUIStore } from '@/stores/uiStore';
import { exportDocx } from '@/lib/api';
import { cn } from '@/lib/utils';
import SeoSection from './SeoSection';
import FusionSections from './FusionSections';

interface ResultCardProps {
  report: Report;
  searchQuery?: string;
}

function getStyleLabel(id: string) {
  return STYLE_OPTIONS.find((s) => s.id === id)?.label || id;
}

export default function ResultCard({ report, searchQuery }: ResultCardProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const { removeReport } = useResultStore();
  const { setPromptModalOpen, setMindmapModalOpen } = useUIStore();

  const charCount = report.content.length;
  const wordCount = report.content.split(/\s+/).filter(Boolean).length;

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

  // 검색어 하이라이트
  const highlightedContent = useMemo(() => {
    if (!searchQuery) return null;
    return report.content;
  }, [report.content, searchQuery]);

  return (
    <Card className="overflow-hidden shadow-sm">
      {/* 헤더 */}
      <div className="px-5 pt-5 pb-2">
        {/* 뱃지 + 액션 */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs px-2.5 py-0.5">
              {getStyleLabel(report.style)}
            </Badge>
            <span className="text-xs text-muted-foreground">{report.time}</span>
            {report.merged && (
              <Badge variant="outline" className="text-xs border-primary/40 text-primary">
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
          </div>
          <div className="flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => copyText(report.title, 'title')}
                >
                  {copiedField === 'title' ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>제목 복사</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => copyText(report.content, 'content')}
                >
                  {copiedField === 'content' ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <FileText className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>전체 복사</TooltipContent>
            </Tooltip>
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
        <h3 className="font-semibold text-lg leading-snug">{report.title}</h3>

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
        <CardContent className="px-5 pb-4 pt-0">
          <div className="prose max-w-none text-[15px] leading-relaxed">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {highlightedContent || report.content}
            </ReactMarkdown>
          </div>

          {/* SEO 섹션 */}
          {report.seo && <SeoSection seo={report.seo} />}

          {/* 퓨전 섹션 */}
          {report.isFusion && (
            <FusionSections sections={report.sections} fusionMeta={report.fusionMeta} />
          )}
        </CardContent>
      )}

      {/* 푸터 */}
      <div className="px-5 py-3 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="inline-flex items-center gap-1">
            <Zap className="h-3.5 w-3.5" />
            {(report.usage?.total_tokens ?? 0).toLocaleString()} tokens
          </span>
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            {(report.elapsed_time ?? 0).toFixed(1)}s
          </span>
          <span className="inline-flex items-center gap-1">
            <Hash className="h-3.5 w-3.5" />
            {charCount.toLocaleString()}자
          </span>
          <span>{wordCount.toLocaleString()}단어</span>
          {report.comment_summary_included && (
            <span className="inline-flex items-center gap-1">
              <MessageSquare className="h-3.5 w-3.5" />
              댓글 포함
            </span>
          )}
        </div>

        <div className="flex items-center gap-0.5">
          {/* 더보기 메뉴 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuItem onClick={() => setPromptModalOpen(true, report.prompt)}>
                <Code className="h-3.5 w-3.5 mr-2" />
                프롬프트 보기
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setMindmapModalOpen(true, report.id)}>
                <Brain className="h-3.5 w-3.5 mr-2" />
                마인드맵
              </DropdownMenuItem>
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
              <DropdownMenuSeparator />
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
  );
}
