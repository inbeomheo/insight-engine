'use client';
/* eslint-disable @next/next/no-img-element */

import { useEffect, useState, type ImgHTMLAttributes } from 'react';
import { apiUrl } from '@/lib/api';
import { authFetch } from '@/lib/auth-session';

type ProtectedImageProps = Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> & {
  src?: string;
};

function canLoadDirectly(src: string): boolean {
  return /^(?:https?:|data:|blob:)/i.test(src);
}

function FetchedProtectedImage({ src, alt = '', ...props }: ProtectedImageProps & { src: string }) {
  const [resolvedSrc, setResolvedSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;

    void authFetch(apiUrl(src), { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setResolvedSrc(objectUrl);
      })
      .catch((error) => {
        if (!controller.signal.aborted && error?.name !== 'AbortError') {
          setFailed(true);
        }
      });

    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src]);

  return (
    <img
      {...props}
      src={resolvedSrc ?? undefined}
      alt={failed ? `${alt} (불러오기 실패)` : alt}
      aria-busy={!failed && Boolean(src) && !resolvedSrc}
    />
  );
}

export default function ProtectedImage({ src, alt = '', ...props }: ProtectedImageProps) {
  if (!src || canLoadDirectly(src)) {
    return <img {...props} src={src || undefined} alt={alt} />;
  }
  return <FetchedProtectedImage key={src} {...props} src={src} alt={alt} />;
}
