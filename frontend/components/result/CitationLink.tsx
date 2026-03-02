'use client';

/**
 * CitationLink — 인용 타임스탬프 링크 컴포넌트
 *
 * 백엔드에서 생성된 .citation-link 클래스 스타일링과 함께,
 * 직접 사용할 수 있는 React 컴포넌트도 제공합니다.
 */

interface CitationLinkProps {
  videoId: string;
  marker: string;   // "[03:25]"
  seconds: number;
}

export function CitationLink({ videoId, marker, seconds }: CitationLinkProps) {
  const url = `https://youtube.com/watch?v=${videoId}&t=${seconds}s`;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-xs align-super text-blue-500 hover:underline hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded px-0.5 no-underline cursor-pointer"
      title={`YouTube ${marker}`}
    >
      {marker}
    </a>
  );
}
