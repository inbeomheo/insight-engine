'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Download, RefreshCw, ImageIcon, Loader2 } from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface ThumbnailPreviewProps {
  title: string;
  keywords?: string[];
}

export default function ThumbnailPreview({ title, keywords = [] }: ThumbnailPreviewProps) {
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateThumbnail = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(apiUrl('/api/generate-thumbnail'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, keywords }),
      });
      const data = await res.json();
      if (!res.ok || !data.success) {
        setError(data.error || '썸네일 생성 실패');
        return;
      }
      setImageBase64(data.image_base64);
    } catch (e) {
      setError('썸네일 생성 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const downloadImage = () => {
    if (!imageBase64) return;
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${imageBase64}`;
    link.download = `${title.slice(0, 30)}_thumbnail.png`;
    link.click();
  };

  return (
    <div className="space-y-3">
      {!imageBase64 && !loading && (
        <Button onClick={generateThumbnail} variant="outline" size="sm" className="gap-2">
          <ImageIcon className="h-4 w-4" />
          썸네일 생성
        </Button>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          AI 썸네일 생성 중...
        </div>
      )}

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {imageBase64 && (
        <div className="space-y-2">
          <img
            src={`data:image/png;base64,${imageBase64}`}
            alt="AI 생성 썸네일"
            className="w-full rounded-lg border"
          />
          <div className="flex gap-2">
            <Button onClick={downloadImage} variant="outline" size="sm" className="gap-2">
              <Download className="h-4 w-4" />
              다운로드
            </Button>
            <Button onClick={generateThumbnail} variant="ghost" size="sm" className="gap-2">
              <RefreshCw className="h-4 w-4" />
              재생성
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
