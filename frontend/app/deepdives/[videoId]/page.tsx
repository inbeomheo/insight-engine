'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, ExternalLink, Image as ImageIcon, Loader2, Save } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import ProtectedImage from '@/components/media/ProtectedImage';
import {
  extractVideoDeepDiveScreenshots,
  fetchVideoDeepDive,
  updateVideoDeepDiveSlides,
  type VideoDeepDiveResponse,
  type VideoDeepDiveSlide,
} from '@/lib/api';

function youtubeAt(sourceUrl: string, seconds?: number): string {
  if (!seconds) return sourceUrl;
  const sep = sourceUrl.includes('?') ? '&' : '?';
  return `${sourceUrl}${sep}t=${Math.floor(seconds)}`;
}

export default function VideoDeepDivePage() {
  const params = useParams<{ videoId: string }>();
  const videoId = decodeURIComponent(params.videoId);
  const [data, setData] = useState<VideoDeepDiveResponse | null>(null);
  const [slides, setSlides] = useState<VideoDeepDiveSlide[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetchVideoDeepDive(videoId)
      .then((res) => {
        if (!alive) return;
        setData(res);
        setSlides(res.meta.slides || []);
      })
      .catch((err) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : '딥다이브를 불러오지 못했어.');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [videoId]);

  const transcriptLines = useMemo(() => (data?.body || '').split('\n').filter(Boolean), [data?.body]);

  async function saveSlides() {
    setSaving(true);
    try {
      const res = await updateVideoDeepDiveSlides(videoId, slides);
      setData((prev) => prev ? { ...prev, meta: res.item } : prev);
      toast.success('노트를 저장했어.');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '노트 저장에 실패했어.');
    } finally {
      setSaving(false);
    }
  }

  async function extractScreenshots() {
    if (!data) return;
    setExtracting(true);
    try {
      toast.info('영상 화면을 추출하는 중이야. 영상 길이에 따라 1~5분 걸릴 수 있어.');
      const res = await extractVideoDeepDiveScreenshots({
        video_id: videoId,
        url: data.meta.source_url,
        title: data.meta.title,
        content: data.meta.visual_suggestions
          .map((cue) => `[${cue.label || (cue.kind === 'screenshot' ? '스크린샷' : '사진')}]: ${cue.description}`)
          .join('\n'),
        transcript: data.body,
        max_slides: Math.min(Math.max(data.meta.visual_suggestions?.length || 6, 4), 8),
        scene_threshold: 0.24,
        min_gap: 8,
      });
      setData((prev) => prev ? { ...prev, meta: res.meta } : prev);
      setSlides(res.slides || res.meta.slides || []);
      toast.success(`스크린샷 ${res.meta.slide_count || res.slides?.length || 0}장을 추출했어.`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '스크린샷 추출에 실패했어.');
    } finally {
      setExtracting(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-background p-6 text-foreground">
        <div className="mx-auto flex max-w-5xl items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          딥다이브를 불러오는 중...
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="min-h-screen bg-background p-6 text-foreground">
        <div className="mx-auto max-w-5xl">
          <Button asChild variant="ghost" className="mb-4 rounded-sm">
            <Link href="/">
              <ArrowLeft className="mr-2 h-4 w-4" />
              돌아가기
            </Link>
          </Button>
          <Card className="rounded-sm border-destructive/30 p-6 text-sm text-destructive">
            {error || '딥다이브를 찾을 수 없어.'}
          </Card>
        </div>
      </main>
    );
  }

  const hasSlides = slides.length > 0;

  return (
    <main className="min-h-screen bg-background p-4 text-foreground sm:p-6 lg:p-8">
      <div className="mx-auto max-w-6xl space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Button asChild variant="ghost" className="rounded-sm">
            <Link href="/">
              <ArrowLeft className="mr-2 h-4 w-4" />
              인사이트 엔진
            </Link>
          </Button>
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" className="rounded-sm border-primary/40 text-primary">
              <a href={data.meta.source_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="mr-2 h-4 w-4" />
                원본 영상
              </a>
            </Button>
            {!hasSlides && (
              <Button onClick={extractScreenshots} disabled={extracting} className="rounded-sm">
                {extracting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ImageIcon className="mr-2 h-4 w-4" />}
                {extracting ? '추출 중...' : '스크린샷 추출'}
              </Button>
            )}
            {hasSlides && (
              <Button onClick={saveSlides} disabled={saving} className="rounded-sm">
                {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                노트 저장
              </Button>
            )}
          </div>
        </div>

        <Card className="rounded-sm border-border bg-card p-6 shadow-none">
          <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.14em] text-primary">Visual Deep Dive</div>
          <h1 className="text-2xl font-black tracking-[-0.03em] sm:text-4xl">{data.meta.title}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {data.meta.slide_count} slides · {data.meta.visual_suggestions?.length || 0} photo cues · {data.meta.created}
          </p>
        </Card>

        {!hasSlides && data.meta.visual_suggestions?.length > 0 && (
          <Card className="rounded-sm border-primary/25 bg-primary/5 p-5 shadow-none">
            <div className="mb-4 flex items-center gap-2">
              <ImageIcon className="h-4 w-4 text-primary" />
              <h2 className="font-bold">사진/스크린샷 큐시트</h2>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {data.meta.visual_suggestions.map((cue) => (
                <div key={`${cue.idx}-${cue.description}`} className="rounded-sm border border-border bg-card p-4">
                  <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.12em] text-primary">
                    {cue.label || (cue.kind === 'screenshot' ? `스크린샷 ${cue.idx}` : `사진 ${cue.idx}`)}
                  </div>
                  {cue.section && <div className="mb-2 text-xs font-semibold text-muted-foreground">{cue.section}</div>}
                  <p className="text-sm leading-6">{cue.description}</p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {hasSlides && (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
            <section className="space-y-4">
              {slides.map((slide, index) => (
                <Card key={`${slide.idx}-${slide.t}`} className="overflow-hidden rounded-sm border-border bg-card shadow-none">
                  {slide.img ? (
                    <ProtectedImage src={slide.img} alt={slide.title || `화면 ${index + 1}`} className="w-full border-b border-border object-cover" />
                  ) : (
                    <div className="flex aspect-video items-center justify-center border-b border-border bg-muted text-muted-foreground">
                      <ImageIcon className="h-8 w-8" />
                    </div>
                  )}
                  <div className="space-y-3 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-primary">{slide.mmss || '00:00'}</div>
                        <h3 className="font-bold">{slide.title || `화면 ${index + 1}`}</h3>
                      </div>
                      <Button asChild size="sm" variant="outline" className="rounded-sm">
                        <a href={youtubeAt(data.meta.source_url, slide.t)} target="_blank" rel="noopener noreferrer">
                          영상 위치
                        </a>
                      </Button>
                    </div>
                    <textarea
                      value={slide.note || ''}
                      onChange={(event) => {
                        const next = [...slides];
                        next[index] = { ...slide, note: event.target.value };
                        setSlides(next);
                      }}
                      placeholder="이 화면에 대한 학습 노트를 적어줘."
                      className="min-h-24 w-full resize-y rounded-sm border border-border bg-background p-3 text-sm outline-none focus:border-primary"
                    />
                    {slide.suggestion && <p className="text-xs text-muted-foreground">추천: {slide.suggestion}</p>}
                  </div>
                </Card>
              ))}
            </section>

            <aside className="lg:sticky lg:top-4 lg:self-start">
              <Card className="max-h-[calc(100vh-2rem)] overflow-auto rounded-sm border-border bg-card p-4 shadow-none">
                <h2 className="mb-3 font-bold">타임스탬프 자막</h2>
                {transcriptLines.length > 0 ? (
                  <div className="space-y-2 text-sm leading-6 text-foreground/80">
                    {transcriptLines.map((line, index) => (
                      <p key={`${index}-${line}`}>{line}</p>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">저장된 자막이 없어.</p>
                )}
              </Card>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
