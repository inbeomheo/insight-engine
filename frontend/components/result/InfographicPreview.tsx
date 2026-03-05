'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { BarChart3, Download, Loader2 } from 'lucide-react';

interface InfographicPreviewProps {
  title: string;
  content: string;
}

export default function InfographicPreview({ title, content }: InfographicPreviewProps) {
  const [htmlContent, setHtmlContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateInfographic = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/export/infographic', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content }),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error || '인포그래픽 생성 실패');
        return;
      }
      const blob = await res.blob();
      const text = await blob.text();
      setHtmlContent(text);
    } catch (e) {
      setError('인포그래픽 생성 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const downloadHtml = () => {
    if (!htmlContent) return;
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${title.slice(0, 30)}_infographic.html`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-3">
      {!htmlContent && !loading && (
        <Button onClick={generateInfographic} variant="outline" size="sm" className="gap-2">
          <BarChart3 className="h-4 w-4" />
          인포그래픽 생성
        </Button>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          인포그래픽 생성 중...
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      {htmlContent && (
        <div className="space-y-2">
          <iframe
            srcDoc={htmlContent}
            className="w-full rounded-lg border bg-white"
            style={{ height: '500px' }}
            title="인포그래픽 미리보기"
            sandbox="allow-same-origin"
          />
          <Button onClick={downloadHtml} variant="outline" size="sm" className="gap-2">
            <Download className="h-4 w-4" />
            HTML 다운로드
          </Button>
        </div>
      )}
    </div>
  );
}
