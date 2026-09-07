'use client';

import { useEffect, useRef, useState } from 'react';
import { Loader2, Download, Music, Video, Image, FileText, Brain, HelpCircle, BookOpen } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { downloadNotebookLmArtifact } from '@/lib/api';
import { useAuthUserId } from '@/hooks/useAuthUserId';
import type { NotebookLmArtifact } from '@/lib/types';

const TYPE_META: Record<string, { label: string; icon: typeof Music }> = {
  audio: { label: '팟캐스트', icon: Music },
  video: { label: '비디오', icon: Video },
  infographic: { label: '인포그래픽', icon: Image },
  slide_deck: { label: '슬라이드', icon: FileText },
  mindmap: { label: '마인드맵', icon: Brain },
  quiz: { label: '퀴즈', icon: HelpCircle },
  flashcards: { label: '플래시카드', icon: BookOpen },
  briefing: { label: '브리핑', icon: FileText },
  study_guide: { label: '스터디 가이드', icon: BookOpen },
};

interface NotebookLmSectionProps {
  artifacts: NotebookLmArtifact[];
}

const FILE_EXTENSIONS: Record<string, string> = {
  audio: 'mp3',
  video: 'mp4',
  infographic: 'png',
  slide_deck: 'pdf',
  mindmap: 'json',
  quiz: 'html',
  flashcards: 'md',
  briefing: 'md',
  study_guide: 'md',
};

const MAX_CACHED_ARTIFACTS = 24;
const artifactBlobCache = new Map<string, Blob>();

interface ArtifactLoad {
  controller: AbortController;
  consumers: number;
  settled: boolean;
  promise: Promise<Blob>;
}

const artifactLoads = new Map<string, ArtifactLoad>();

function cacheArtifact(artifactId: string, blob: Blob): Blob {
  artifactBlobCache.delete(artifactId);
  artifactBlobCache.set(artifactId, blob);
  while (artifactBlobCache.size > MAX_CACHED_ARTIFACTS) {
    const oldest = artifactBlobCache.keys().next().value;
    if (oldest === undefined) break;
    artifactBlobCache.delete(oldest);
  }
  return blob;
}

function acquireArtifactBlob(artifactId: string, authScope: string): {
  promise: Promise<Blob>;
  release: () => void;
} {
  const cacheKey = `${authScope}:${artifactId}`;
  const cached = artifactBlobCache.get(cacheKey);
  if (cached) {
    // 접근 순서로 작은 LRU 캐시를 유지한다.
    cacheArtifact(cacheKey, cached);
    return { promise: Promise.resolve(cached), release: () => {} };
  }

  let load = artifactLoads.get(cacheKey);
  if (!load) {
    const controller = new AbortController();
    load = {
      controller,
      consumers: 0,
      settled: false,
      promise: Promise.resolve(new Blob()),
    };
    const currentLoad = load;
    currentLoad.promise = downloadNotebookLmArtifact(
      artifactId,
      controller.signal,
    )
      .then((blob) => cacheArtifact(cacheKey, blob))
      .finally(() => {
        currentLoad.settled = true;
        if (artifactLoads.get(cacheKey) === currentLoad) {
          artifactLoads.delete(cacheKey);
        }
      });
    artifactLoads.set(cacheKey, currentLoad);
  }

  load.consumers += 1;
  let released = false;
  return {
    promise: load.promise,
    release: () => {
      if (released) return;
      released = true;
      load!.consumers = Math.max(0, load!.consumers - 1);
      if (load!.consumers === 0 && !load!.settled) {
        load!.controller.abort();
      }
    },
  };
}

async function downloadArtifact(artifact: NotebookLmArtifact, authScope: string) {
  const acquired = acquireArtifactBlob(artifact.artifact_id, authScope);
  try {
    const blob = await acquired.promise;
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    const safeId = artifact.artifact_id.replace(/[^a-zA-Z0-9._-]/g, '_');
    anchor.download = `${safeId}.${FILE_EXTENSIONS[artifact.content_type] || 'bin'}`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') return;
    toast.error(error instanceof Error ? error.message : '다운로드에 실패했습니다.');
  } finally {
    acquired.release();
  }
}

function AuthenticatedAudio({
  artifact,
  authScope,
}: {
  artifact: NotebookLmArtifact;
  authScope: string;
}) {
  const [source, setSource] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const generationRef = useRef(0);
  const releaseRef = useRef<(() => void) | null>(null);
  const sourceRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      generationRef.current += 1;
      releaseRef.current?.();
      releaseRef.current = null;
      if (sourceRef.current) URL.revokeObjectURL(sourceRef.current);
      sourceRef.current = null;
    };
  }, []);

  async function loadAudio() {
    if (status === 'loading' || status === 'ready') return;
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    setStatus('loading');
    const acquired = acquireArtifactBlob(artifact.artifact_id, authScope);
    releaseRef.current = acquired.release;
    try {
      const blob = await acquired.promise;
      if (generationRef.current !== generation) return;
      const objectUrl = URL.createObjectURL(blob);
      if (sourceRef.current) URL.revokeObjectURL(sourceRef.current);
      sourceRef.current = objectUrl;
      setSource(objectUrl);
      setStatus('ready');
    } catch (error) {
      if (
        generationRef.current === generation
        && !(error instanceof DOMException && error.name === 'AbortError')
      ) {
        setStatus('error');
      }
    } finally {
      acquired.release();
      if (releaseRef.current === acquired.release) releaseRef.current = null;
    }
  }

  if (status === 'idle') {
    return (
      <Button
        variant="outline"
        size="sm"
        className="h-8 text-xs"
        onClick={() => void loadAudio()}
        aria-label="오디오 불러오기"
      >
        <Music className="mr-1.5 h-3.5 w-3.5" />
        오디오 불러오기
      </Button>
    );
  }
  if (status === 'loading') {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        오디오를 불러오는 중...
      </p>
    );
  }
  if (status === 'error') {
    return (
      <div className="flex items-center gap-2 text-xs text-destructive">
        <span>오디오를 불러오지 못했습니다.</span>
        <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => void loadAudio()}>
          다시 시도
        </Button>
      </div>
    );
  }
  return <audio controls className="h-8 w-full" preload="metadata" src={source ?? undefined} />;
}

export function NotebookLmSection({ artifacts }: NotebookLmSectionProps) {
  const authUserId = useAuthUserId();
  const authScope = authUserId ? `user:${authUserId}` : 'anonymous';
  if (!artifacts || artifacts.length === 0) return null;

  return (
    <div className="mt-3 border-t border-border/40 pt-3">
      <p className="text-xs font-medium text-muted-foreground mb-2">NotebookLM</p>
      <div className="flex flex-wrap gap-2">
        {artifacts.map((a) => {
          const meta = TYPE_META[a.content_type] ?? { label: a.content_type, icon: FileText };
          const Icon = meta.icon;

          if (a.status === 'in_progress') {
            return (
              <div key={a.artifact_id} className="flex items-center gap-1.5 text-xs text-muted-foreground bg-muted/50 rounded-md px-2.5 py-1.5">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>{meta.label} 생성 중...</span>
              </div>
            );
          }

          if (a.status === 'failed') {
            return (
              <div key={a.artifact_id} className="flex items-center gap-1.5 text-xs text-destructive bg-destructive/10 rounded-md px-2.5 py-1.5">
                <Icon className="h-3.5 w-3.5" />
                <span>{meta.label} 실패</span>
              </div>
            );
          }

          // completed
          if (a.content_type === 'audio') {
            return (
              <div key={a.artifact_id} className="w-full">
                <div className="flex items-center gap-2 mb-1">
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium">{meta.label}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 ml-auto"
                    onClick={() => void downloadArtifact(a, authScope)}
                    aria-label={`${meta.label} 다운로드`}
                  >
                    <Download className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <AuthenticatedAudio
                  key={`${authScope}:${a.artifact_id}`}
                  artifact={a}
                  authScope={authScope}
                />
              </div>
            );
          }

          return (
            <Button
              key={a.artifact_id}
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1.5"
              onClick={() => void downloadArtifact(a, authScope)}
            >
              <Icon className="h-3.5 w-3.5" />
              {meta.label}
              <Download className="h-3 w-3" />
            </Button>
          );
        })}
      </div>
    </div>
  );
}
