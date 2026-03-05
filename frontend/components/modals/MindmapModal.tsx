'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Brain, Download, Image, Loader2 } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useResultStore } from '@/stores/resultStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { generateMindmap } from '@/lib/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from 'sonner';
import { useCallback, useRef } from 'react';

/** SVG 요소를 Blob으로 변환 */
function svgToBlob(svgEl: SVGSVGElement): Blob {
  const serializer = new XMLSerializer();
  const svgStr = serializer.serializeToString(svgEl);
  return new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
}

/** Blob을 다운로드 */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function MindmapModal() {
  const { activeModal, activeMindmapReportId, setMindmapModalOpen } = useUIStore();
  const mindmapModalOpen = activeModal === 'mindmap';
  const { reports, updateReport } = useResultStore();
  const { selectedModel } = useSettingsStore();
  const [loading, setLoading] = useState(false);
  const [markdown, setMarkdown] = useState('');
  const contentRef = useRef<HTMLDivElement>(null);

  const report = reports.find((r) => r.id === activeMindmapReportId);

  useEffect(() => {
    if (!mindmapModalOpen || !report) return;

    // 캐시된 마인드맵이 있으면 사용
    if (report.mindmapMarkdown) {
      setMarkdown(report.mindmapMarkdown);
      return;
    }

    // 새로 생성
    setLoading(true);
    generateMindmap(report.content, report.title, selectedModel)
      .then((res) => {
        setMarkdown(res.markdown);
        updateReport(report.id, { mindmapMarkdown: res.markdown });
      })
      .catch(() => toast.error('마인드맵 생성 실패'))
      .finally(() => setLoading(false));
  }, [mindmapModalOpen, report, updateReport]);

  /** 마인드맵 영역에서 SVG를 찾아 반환 */
  const findSvg = useCallback((): SVGSVGElement | null => {
    return contentRef.current?.querySelector('svg') ?? null;
  }, []);

  /** SVG 파일 다운로드 */
  const handleDownloadSvg = useCallback(() => {
    const svg = findSvg();
    if (!svg) {
      toast.error('내보낼 SVG가 없습니다');
      return;
    }
    const blob = svgToBlob(svg);
    downloadBlob(blob, `mindmap-${Date.now()}.svg`);
    toast.success('SVG 다운로드 완료');
  }, [findSvg]);

  /** PNG 파일 다운로드 (SVG → Canvas → PNG) */
  const handleDownloadPng = useCallback(() => {
    const svg = findSvg();
    if (!svg) {
      toast.error('내보낼 SVG가 없습니다');
      return;
    }
    const blob = svgToBlob(svg);
    const url = URL.createObjectURL(blob);
    const img = new window.Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const scale = 2; // 고해상도
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0);
      canvas.toBlob((pngBlob) => {
        if (pngBlob) {
          downloadBlob(pngBlob, `mindmap-${Date.now()}.png`);
          toast.success('PNG 다운로드 완료');
        }
      }, 'image/png');
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      toast.error('PNG 변환 실패');
      URL.revokeObjectURL(url);
    };
    img.src = url;
  }, [findSvg]);

  return (
    <Dialog open={mindmapModalOpen} onOpenChange={(v) => setMindmapModalOpen(v)}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            마인드맵
          </DialogTitle>
          <DialogDescription>콘텐츠를 구조화된 마인드맵으로 확인합니다</DialogDescription>
          {!loading && markdown && (
            <div className="flex gap-2 mt-2">
              <Button variant="outline" size="sm" onClick={handleDownloadSvg}>
                <Download className="h-4 w-4 mr-1" /> SVG
              </Button>
              <Button variant="outline" size="sm" onClick={handleDownloadPng}>
                <Image className="h-4 w-4 mr-1" /> PNG
              </Button>
            </div>
          )}
        </DialogHeader>

        <ScrollArea className="flex-1 max-h-[70vh]">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="ml-3 text-sm text-muted-foreground">마인드맵 생성 중...</span>
            </div>
          ) : (
            <div ref={contentRef} className="prose max-w-none p-4">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
